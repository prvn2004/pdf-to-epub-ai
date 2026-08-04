export class AppState extends EventTarget {
  constructor() {
    super();
    this.state = {
      jobId: null,
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
    this.dispatchEvent(new CustomEvent('statechange', { detail: { key, value, state: this.state } }));
    this.dispatchEvent(new CustomEvent(`change:${key}`, { detail: value }));
  }

  updatePageData(pageno, text) {
    this.state.pagesData[pageno] = text;
    this.dispatchEvent(new CustomEvent('page:added', { detail: { pageno, text } }));
  }
}

export const store = new AppState();
