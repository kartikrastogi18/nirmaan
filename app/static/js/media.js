/* Site-update media helpers: camera, recording, speech recognition and previews. */
function supportsCamera() {
  return !!(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

function supportsRecording() {
  return !!(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
}

function preferredAudioMimeType() {
  if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return "";
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"].find(t => MediaRecorder.isTypeSupported(t)) || "";
}

function audioExtension(type) {
  if ((type || "").includes("ogg")) return "ogg";
  if ((type || "").includes("mp4")) return "m4a";
  return "webm";
}

function stopMediaStream(stream) {
  if (stream) stream.getTracks().forEach(track => track.stop());
}

function dataUrlToFile(dataUrl, filename) {
  const parts = dataUrl.split(",");
  const mime = (parts[0].match(/data:(.*?);/) || [])[1] || "image/jpeg";
  const binary = atob(parts[1]);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new File([bytes], filename, { type: mime });
}
