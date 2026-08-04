import { store } from '../state.js';

export class ReaderComponent {
  constructor() {
    this.bookPages = document.getElementById('bookPages');
    this.initEvents();
  }

  initEvents() {
    store.addEventListener('page:added', e => {
      const { pageno, text } = e.detail;
      this.addBookPage(pageno, text);
    });

    store.addEventListener('change:jobId', () => {
      this.bookPages.innerHTML = '<div class="empty-state">Processing started...</div>';
    });
  }

  mdToHtml(md) {
    if (!md) return '<p><em>(empty page)</em></p>';
    let h = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // Images: ![alt](src)
    h = h.replace(/!\[([^\]]*)\]\(([^)]+)\)/g,
      '<figure><img src="$2" alt="$1" loading="lazy"/><figcaption>$1</figcaption></figure>');
    // Code blocks
    h = h.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    // Headings
    h = h.replace(/^###### (.*)$/gm, '<h6>$1</h6>');
    h = h.replace(/^##### (.*)$/gm, '<h5>$1</h5>');
    h = h.replace(/^#### (.*)$/gm, '<h4>$1</h4>');
    h = h.replace(/^### (.*)$/gm, '<h3>$1</h3>');
    h = h.replace(/^## (.*)$/gm, '<h2>$1</h2>');
    h = h.replace(/^# (.*)$/gm, '<h1>$1</h1>');
    // Horizontal rule
    h = h.replace(/^---+$/gm, '<hr/>');
    // Blockquotes
    h = h.replace(/^&gt; (.*)$/gm, '<blockquote>$1</blockquote>');
    // Inline code
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold, then italic
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    // List items
    h = h.replace(/^[-*] (.*)$/gm, '<li>$1</li>');
    h = h.replace(/^\d+\. (.*)$/gm, '<li>$1</li>');

    const out = [];
    for (const p of h.split(/\n{2,}/)) {
      const t = p.trim();
      if (!t) continue;
      if (/^<(h[1-6]|hr|pre|figure|blockquote)/.test(t)) out.push(t);
      else if (t.includes('<li>')) out.push('<ul>' + t.replace(/\n/g, '') + '</ul>');
      else out.push(`<p>${t.replace(/\n/g, '<br/>')}</p>`);
    }
    return out.join('');
  }

  addBookPage(pageno, text) {
    // Clear empty state on first page
    const emptyState = this.bookPages.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    let div = document.getElementById(`page-${pageno}`);
    if (!div) {
      div = document.createElement('div');
      div.className = 'book-page';
      div.id = `page-${pageno}`;
      this.bookPages.appendChild(div);
    }

    div.innerHTML = `<h2>Page ${pageno}</h2>` + this.mdToHtml(text);
    div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
}
