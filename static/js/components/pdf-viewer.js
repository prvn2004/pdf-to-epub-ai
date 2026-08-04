import { store } from '../state.js';
import { ApiClient } from '../api.js';

export class PdfViewerComponent {
  constructor() {
    this.pdfImg = document.getElementById('pdfImage');
    this.pageIndicator = document.getElementById('pageIndicator');
    this.btnPrev = document.getElementById('btnPrev');
    this.btnNext = document.getElementById('btnNext');

    this.initEvents();
  }

  initEvents() {
    this.btnPrev.addEventListener('click', () => {
      const cur = store.get('currentPage');
      if (cur > 0) store.set('currentPage', cur - 1);
    });

    this.btnNext.addEventListener('click', () => {
      const cur = store.get('currentPage');
      const total = store.get('totalPages');
      if (cur < total - 1) store.set('currentPage', cur + 1);
    });

    store.addEventListener('change:currentPage', e => this.loadPage(e.detail));
    store.addEventListener('change:totalPages', () => this.updateIndicator());
  }

  loadPage(pageIdx) {
    const jobId = store.get('jobId');
    if (!jobId) return;

    const url = ApiClient.getPreviewUrl(jobId, pageIdx);
    this.pdfImg.onerror = () => {
      setTimeout(() => {
        if (this.pdfImg.src === url || this.pdfImg.src.endsWith(url)) {
          this.pdfImg.src = url + '?retry=' + Date.now();
        }
      }, 1000);
    };
    this.pdfImg.src = url;
    this.updateIndicator();
  }

  updateIndicator() {
    const pageIdx = store.get('currentPage') || 0;
    const total = store.get('totalPages') || 0;
    this.pageIndicator.textContent = `Page ${pageIdx + 1} of ${total}`;
  }
}
