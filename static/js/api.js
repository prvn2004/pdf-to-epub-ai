export class ApiClient {
  static async uploadPdf(file, title, author) {
    const form = new FormData();
    form.append('file', file);
    form.append('title', title);
    form.append('author', author);

    const resp = await fetch('/api/upload', { method: 'POST', body: form });
    if (!resp.ok) throw new Error(`Upload failed: ${resp.statusText}`);
    return await resp.json();
  }

  static async getPdfInfo(jobId) {
    const resp = await fetch(`/api/pdf_info/${jobId}`);
    if (!resp.ok) throw new Error(`Failed to fetch PDF info: ${resp.statusText}`);
    return await resp.json();
  }

  static async getSession(jobId) {
    const resp = await fetch(`/api/session/${jobId}`);
    if (!resp.ok) throw new Error(`Failed to fetch session: ${resp.statusText}`);
    return await resp.json();
  }

  static async resumeJob(jobId) {
    const resp = await fetch(`/api/resume/${jobId}`, { method: 'POST' });
    if (!resp.ok) throw new Error(`Failed to resume job: ${resp.statusText}`);
    return await resp.json();
  }

  static getDownloadUrl(jobId) {
    return `/download/${jobId}`;
  }

  static getPreviewUrl(jobId, pageIdx) {
    return `/api/preview/${jobId}/${pageIdx}`;
  }
}
