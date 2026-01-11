document$.subscribe(() => {
  mermaid.initialize({
    theme: document.body.getAttribute('data-md-color-scheme') === 'slate' ? 'dark' : 'default'
  });
})
