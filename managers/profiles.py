"""Agent profiles system for customizing AI behavior and capabilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class AgentProfile:
    """Configuration profile for an AI agent."""

    id: str
    name: str
    description: str
    icon: str = "🤖"

    # Behavior
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int | None = None

    # Tools
    allowed_tools: list[str] | None = None  # None = all
    blocked_tools: list[str] = field(default_factory=list)

    # Context
    auto_include_files: list[str] = field(default_factory=list)  # Glob patterns
    context_instructions: str = ""

    # Guardrails
    require_approval: list[str] = field(
        default_factory=list
    )  # Tool names requiring approval
    max_iterations: int = 10

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    source: Literal["builtin", "local"] = "local"

    def to_dict(self) -> dict:
        """Convert profile to dictionary, handling datetime serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> AgentProfile:
        """Create profile from dictionary, handling datetime deserialization."""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class ProfileManager:
    """Manages agent profiles with persistence and builtin defaults."""

    def __init__(self, profiles_dir: Path | None = None):
        self.profiles_dir = profiles_dir or Path.home() / ".null" / "profiles"
        self.profiles: dict[str, AgentProfile] = {}
        self.active_profile_id: str | None = None
        self._builtin_profiles_created = False

    def initialize(self) -> None:
        """Initialize manager: create directory, load profiles, and create builtins."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.load_profiles()
        if not self._builtin_profiles_created:
            self.create_builtin_profiles()

    def load_profiles(self) -> None:
        """Load all profiles from directory."""
        self.profiles.clear()

        if not self.profiles_dir.exists():
            return

        for yaml_file in self.profiles_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data:
                        profile = AgentProfile.from_dict(data)
                        self.profiles[profile.id] = profile
            except Exception as e:
                # Log error but continue loading other profiles
                print(f"Error loading profile {yaml_file}: {e}")

    def save_profile(self, profile: AgentProfile) -> Path:
        """Save profile to YAML file."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        filepath = self.profiles_dir / f"{profile.id}.yaml"

        # Convert to dict for YAML serialization
        data = profile.to_dict()

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self.profiles[profile.id] = profile
        return filepath

    def get_profile(self, profile_id: str) -> AgentProfile | None:
        """Get a profile by ID."""
        return self.profiles.get(profile_id)

    @property
    def active_profile(self) -> AgentProfile | None:
        """Get the currently active profile."""
        if self.active_profile_id:
            return self.profiles.get(self.active_profile_id)
        return None

    def activate(self, profile_id: str) -> bool:
        """Set the active profile."""
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            return True
        return False

    def list_profiles(self, tags: list[str] | None = None) -> list[AgentProfile]:
        """List profiles, optionally filtered by tags."""
        profiles = list(self.profiles.values())

        if tags:
            profiles = [p for p in profiles if any(tag in p.tags for tag in tags)]

        return sorted(profiles, key=lambda p: p.name)

    def create_builtin_profiles(self) -> None:
        """Create default builtin profiles."""
        builtins = [
            AgentProfile(
                id="default",
                name="Default Assistant",
                description="General-purpose AI assistant for any task",
                icon="🤖",
                system_prompt="""You are a helpful, intelligent assistant. You can:
- Answer questions on any topic
- Help with coding, writing, analysis
- Execute tools and commands when needed
- Provide detailed explanations

Be concise but thorough. Ask clarifying questions when needed.""",
                temperature=0.7,
                max_tokens=None,
                allowed_tools=None,  # All tools allowed
                blocked_tools=[],
                auto_include_files=[],
                context_instructions="",
                require_approval=[],
                max_iterations=10,
                tags=["general", "assistant"],
                source="builtin",
            ),
            AgentProfile(
                id="frontend",
                name="Frontend Developer",
                description="Specializes in React, TypeScript, CSS, and web UI",
                icon="🎨",
                system_prompt="""You are a frontend development expert specializing in:
- React and Next.js
- TypeScript and JavaScript
- Tailwind CSS and CSS-in-JS
- Accessibility (WCAG)
- Performance optimization
- Component design patterns

Provide clean, maintainable code with proper typing. Consider accessibility and performance.""",
                temperature=0.3,
                max_tokens=None,
                allowed_tools=["read_file", "write_file", "run_command"],
                blocked_tools=[],
                auto_include_files=[
                    "package.json",
                    "tsconfig.json",
                    "tailwind.config.js",
                ],
                context_instructions="Always check package.json for dependencies and tsconfig.json for configuration.",
                require_approval=["write_file"],
                max_iterations=10,
                tags=["frontend", "react", "typescript", "css"],
                source="builtin",
            ),
            AgentProfile(
                id="backend",
                name="Backend Developer",
                description="Specializes in Python, APIs, databases, and infrastructure",
                icon="⚙️",
                system_prompt="""You are a backend development expert specializing in:
- Python (FastAPI, Django, Flask)
- REST APIs and GraphQL
- Database design (SQL, NoSQL)
- Authentication and security
- Microservices architecture
- DevOps and deployment

Write secure, scalable, well-tested code. Follow best practices for error handling and logging.""",
                temperature=0.3,
                max_tokens=None,
                allowed_tools=["read_file", "write_file", "run_command"],
                blocked_tools=[],
                auto_include_files=["requirements.txt", "pyproject.toml", "setup.py"],
                context_instructions="Check requirements.txt for dependencies and understand the project structure.",
                require_approval=["write_file"],
                max_iterations=10,
                tags=["backend", "python", "api", "database"],
                source="builtin",
            ),
            AgentProfile(
                id="devops",
                name="DevOps Engineer",
                description="Specializes in Docker, CI/CD, infrastructure, and deployment",
                icon="🚀",
                system_prompt="""You are a DevOps engineer specializing in:
- Docker and containerization
- Kubernetes orchestration
- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
- Infrastructure as Code (Terraform, CloudFormation)
- Cloud platforms (AWS, GCP, Azure)
- Monitoring and logging
- Security and compliance

Provide production-ready configurations with proper error handling and monitoring.""",
                temperature=0.3,
                max_tokens=None,
                allowed_tools=["read_file", "write_file", "run_command"],
                blocked_tools=[],
                auto_include_files=[
                    "Dockerfile",
                    "docker-compose.yml",
                    ".github/workflows",
                ],
                context_instructions="Review Dockerfile and docker-compose.yml for current setup.",
                require_approval=["run_command"],
                max_iterations=10,
                tags=["devops", "docker", "ci-cd", "infrastructure"],
                source="builtin",
            ),
            AgentProfile(
                id="security",
                name="Security Specialist",
                description="Specializes in security review, hardening, and vulnerability analysis",
                icon="🔒",
                system_prompt="""You are a security specialist focusing on:
- Vulnerability assessment and remediation
- Secure coding practices
- Authentication and authorization
- Encryption and cryptography
- OWASP Top 10 prevention
- Security hardening
- Compliance (GDPR, HIPAA, SOC2)

Identify risks, explain threats clearly, and provide actionable mitigations.""",
                temperature=0.3,
                max_tokens=None,
                allowed_tools=["read_file", "write_file", "run_command"],
                blocked_tools=[],
                auto_include_files=["requirements.txt", "package.json", "Dockerfile"],
                context_instructions="Review dependencies, code, and configurations for security issues.",
                require_approval=["write_file", "run_command"],
                max_iterations=10,
                tags=["security", "hardening", "vulnerability"],
                source="builtin",
            ),
        ]

        for profile in builtins:
            self.profiles[profile.id] = profile

        self._builtin_profiles_created = True

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile (local only, not builtin)."""
        profile = self.profiles.get(profile_id)
        if not profile or profile.source == "builtin":
            return False

        filepath = self.profiles_dir / f"{profile_id}.yaml"
        if filepath.exists():
            filepath.unlink()

        del self.profiles[profile_id]

        if self.active_profile_id == profile_id:
            self.active_profile_id = None

        return True

    def export_profile(self, profile_id: str) -> str | None:
        """Export profile as YAML string."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return None

        data = profile.to_dict()
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def import_profile(self, yaml_content: str) -> AgentProfile | None:
        """Import profile from YAML string."""
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                return None

            profile = AgentProfile.from_dict(data)
            self.save_profile(profile)
            return profile
        except Exception:
            return None

    def duplicate_profile(
        self, source_id: str, new_id: str, new_name: str
    ) -> AgentProfile | None:
        """Create a copy of an existing profile with a new ID."""
        source = self.profiles.get(source_id)
        if not source:
            return None

        # Create new profile with copied data
        new_profile = AgentProfile(
            id=new_id,
            name=new_name,
            description=source.description,
            icon=source.icon,
            system_prompt=source.system_prompt,
            temperature=source.temperature,
            max_tokens=source.max_tokens,
            allowed_tools=source.allowed_tools.copy() if source.allowed_tools else None,
            blocked_tools=source.blocked_tools.copy(),
            auto_include_files=source.auto_include_files.copy(),
            context_instructions=source.context_instructions,
            require_approval=source.require_approval.copy(),
            max_iterations=source.max_iterations,
            tags=source.tags.copy(),
            source="local",
        )

        self.save_profile(new_profile)
        return new_profile
