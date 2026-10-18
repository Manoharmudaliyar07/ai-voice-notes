// Thin wrapper around the Flask API. Every function throws an Error whose
// message is safe to show directly to the user.

async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure the Flask server is running on port 5000."
    );
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const data = await res.json();
      if (data.error) message = data.error;
    } catch {
      /* response was not JSON; keep the generic message */
    }
    throw new Error(message);
  }
  return res;
}

export async function getHealth() {
  const res = await request("/api/health");
  return res.json();
}

export async function transcribeAudio(file, language) {
  const form = new FormData();
  form.append("audio", file, file.name);
  form.append("language", language);
  const res = await request("/api/transcribe", { method: "POST", body: form });
  return res.json();
}

export async function analyzeText(text) {
  const res = await request("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return res.json();
}

// Asks the backend to build the file, then triggers a browser download.
export async function downloadNotes(format, payload) {
  const res = await request(`/api/export/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `voice-notes.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
