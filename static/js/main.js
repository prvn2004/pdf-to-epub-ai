import { DropzoneComponent } from './components/dropzone.js';
import { PdfViewerComponent } from './components/pdf-viewer.js';
import { ReaderComponent } from './components/reader.js';
import { TelemetryComponent } from './components/telemetry.js';

document.addEventListener('DOMContentLoaded', () => {
  new DropzoneComponent();
  new PdfViewerComponent();
  new ReaderComponent();
  new TelemetryComponent();
});
