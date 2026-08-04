export class AppState extends EventTarget {
  constructor() {
    super();
    this.state = {
      jobId: localStorage.getItem('folio_active_job') || null,
      totalPages: 0,
      currentPage: 0,
      pagesDone: 0,
      startTime: 0,
      pagesData: {},
      ocrTimes: [],
      isProcessing: false,
      isCompleted: false,
    };
  }

  get(key) {
    return this.state[key];
  }

  set(key, value) {
    this.state[key] = value;
    if (key === 'jobId') {
      if (value) localStorage.setItem('folio_active_job', value);
      else localStorage.removeItem('folio_active_job');
    }
    this.dispatchEvent(new CustomEvent('statechange', { detail: { key, value, state: this.state } }));
    this.dispatchEvent(new CustomEvent(`change:${key}`, { detail: value }));
  }

  updatePageData(pageno, text) {
    this.state.pagesData[pageno] = text;
    this.dispatchEvent(new CustomEvent('page:added', { detail: { pageno, text } }));
  }

  restorePages(completedPages) {
    this.state.pagesData = {};
    const keys = Object.keys(completedPages).map(Number).sort((a, b) => a - b);
    for (const pageno of keys) {
      const p_data = completedPages[pageno];
      this.state.pagesData[pageno] = p_data.text;
      this.dispatchEvent(new CustomEvent('page:added', { detail: { pageno, text: p_data.text } }));
    }
  }

  clearJob() {
    localStorage.removeItem('folio_active_job');
    this.state.jobId = null;
    this.state.totalPages = 0;
    this.state.currentPage = 0;
    this.state.pagesData = {};
    this.state.isProcessing = false;
    this.state.isCompleted = false;
  }
}

export const store = new AppState();
