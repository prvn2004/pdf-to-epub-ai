import { store } from '../state.js';

export class ReaderComponent {
  constructor() {
    this.bookPages = document.getElementById('bookPages');
    this.maxPagenoSeen = 0;
    this.initEvents();
  }

  initEvents() {
    store.addEventListener('page:added', e => {
      const { pageno, text } = e.detail;
      this.addBookPage(pageno, text);
    });

    store.addEventListener('change:jobId', () => {
      this.maxPagenoSeen = 0;
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
    const emptyState = this.bookPages.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const numPageno = Number(pageno);

    let div = document.getElementById(`page-${numPageno}`);
    if (!div) {
      div = document.createElement('div');
      div.className = 'book-page';
      div.id = `page-${numPageno}`;
      div.dataset.pageno = numPageno;

      // Maintain strict numerical page order in the DOM
      const existingPages = Array.from(this.bookPages.querySelectorAll('.book-page[data-pageno]'));
      const nextSibling = existingPages.find(el => Number(el.dataset.pageno) > numPageno);

      if (nextSibling) {
        this.bookPages.insertBefore(div, nextSibling);
      } else {
        this.bookPages.appendChild(div);
      }
    } else {
      div.dataset.pageno = numPageno;
    }

    div.innerHTML = `<h2>Page ${numPageno}</h2>` + this.mdToHtml(text);

    // Smoothly scroll to newly added page if it's the highest page seen so far
    if (numPageno > this.maxPagenoSeen) {
      this.maxPagenoSeen = numPageno;
      div.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }
}
