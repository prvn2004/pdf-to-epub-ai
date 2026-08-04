import { store } from '../state.js';
import { ApiClient } from '../api.js';
import { sseManager } from '../sse.js';

export class DropzoneComponent {
  constructor() {
    this.dz = document.getElementById('dropzone');
    this.fileInput = document.getElementById('fileInput');
    this.ws = document.getElementById('workspace');
    this.metaTitle = document.getElementById('metaTitle');
    this.metaAuthor = document.getElementById('metaAuthor');

    this.initEvents();
  }

  initEvents() {
    this.dz.addEventListener('click', () => this.fileInput.click());
    this.dz.addEventListener('dragover', e => { e.preventDefault(); this.dz.classList.add('drag'); });
    this.dz.addEventListener('dragleave', () => this.dz.classList.remove('drag'));
    this.dz.addEventListener('drop', e => {
      e.preventDefault();
      this.dz.classList.remove('drag');
      if (e.dataTransfer.files.length) this.handleFile(e.dataTransfer.files[0]);
    });
    this.fileInput.addEventListener('change', () => {
      if (this.fileInput.files.length) this.handleFile(this.fileInput.files[0]);
    });
  }

  async handleFile(file) {
    if (!file.name.endsWith('.pdf')) return alert('Please select a PDF file.');

    const title = this.metaTitle.value || file.name.replace(/\.pdf$/i, '');
    const author = this.metaAuthor.value || 'Unknown';

    this.dz.classList.add('hidden');
    this.ws.classList.add('active');
    store.set('progressMsg', 'Uploading...');
    store.set('isProcessing', true);
    store.set('startTime', Date.now());

    try {
      const data = await ApiClient.uploadPdf(file, title, author);
      store.set('jobId', data.job_id);

      const info = await ApiClient.getPdfInfo(data.job_id);
      store.set('totalPages', info.pages);
      store.set('currentPage', 0);

      sseManager.listen(data.job_id);
    } catch (err) {
      alert(`Error starting processing: ${err.message}`);
      this.dz.classList.remove('hidden');
      this.ws.classList.remove('active');
    }
  }
}
