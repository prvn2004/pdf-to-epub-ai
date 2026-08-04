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
    this.dz.addEventListener('click', e => {
      if (e.target.tagName !== 'INPUT') {
        this.fileInput.click();
      }
    });
    this.dz.addEventListener('dragover', e => { e.preventDefault(); this.dz.classList.add('drag'); });
    this.dz.addEventListener('dragleave', () => this.dz.classList.remove('drag'));
    this.dz.addEventListener('drop', e => {
      e.preventDefault();
      this.dz.classList.remove('drag');
      if (e.dataTransfer.files.length) this.handleFiles(Array.from(e.dataTransfer.files));
    });
    this.fileInput.addEventListener('change', () => {
      if (this.fileInput.files.length) this.handleFiles(Array.from(this.fileInput.files));
    });
  }

  async handleFiles(files) {
    const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfFiles.length) return alert('Please select valid PDF file(s).');

    const title = this.metaTitle ? this.metaTitle.value : '';
    const author = this.metaAuthor ? this.metaAuthor.value : '';

    this.dz.classList.add('hidden');
    this.ws.classList.add('active');
    store.set('progressMsg', `Uploading ${pdfFiles.length} file(s)...`);
    store.set('isProcessing', true);
    store.set('startTime', Date.now());

    try {
      const data = await ApiClient.batchUpload(pdfFiles, title, author);
      if (data.jobs && data.jobs.length > 0) {
        const firstJob = data.jobs[0];
        store.set('jobId', firstJob.job_id);

        const info = await ApiClient.getPdfInfo(firstJob.job_id);
        store.set('totalPages', info.pages);
        store.set('currentPage', 0);

        sseManager.listen(firstJob.job_id);
      }
    } catch (err) {
      alert(`Error starting batch upload: ${err.message}`);
      this.dz.classList.remove('hidden');
      this.ws.classList.remove('active');
    }
  }
}
