const baseUrl = window.location.origin;
const MAX_RECORDING_SECONDS = 60;
const THEME_KEY = "voice-assistant-theme";
const AVATAR_ICONS = { user: "fa-user", bot: "fa-microphone", error: "fa-exclamation" };

let recorder = null;
let recording = false;
let busy = false;
let recordingTimer = null;
let currentAudio = null;

// Throws the server's error message so it can be shown in the chat
const parseResponse = async (res) => {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "An error occurred. Please try again.");
  }
  return data;
};

const getSpeechToText = async (userRecording) => {
  const res = await fetch(baseUrl + "/speech-to-text", {
    method: "POST",
    headers: { "Content-Type": userRecording.audioBlob.type || "application/octet-stream" },
    body: userRecording.audioBlob,
  });
  const data = await parseResponse(res);
  return data.text;
};

const processUserMessage = async (userMessage) => {
  const res = await fetch(baseUrl + "/process-message", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ userMessage }),
  });
  return parseResponse(res);
};

const cleanTextInput = (value) => value.replace(/[\n\t]/g, " ").trim();

const recordAudio = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  const audioChunks = [];

  mediaRecorder.addEventListener("dataavailable", (event) => {
    audioChunks.push(event.data);
  });

  const start = () => mediaRecorder.start();

  const stop = () =>
    new Promise((resolve) => {
      mediaRecorder.addEventListener("stop", () => {
        stream.getTracks().forEach((track) => track.stop()); // release the microphone
        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
        resolve({ audioBlob, audioUrl: URL.createObjectURL(audioBlob) });
      });

      mediaRecorder.stop();
    });

  return { start, stop };
};

// Only one clip plays at a time; the active replay button is highlighted
const stopAudio = () => {
  if (currentAudio) {
    currentAudio.audio.pause();
    currentAudio.button?.removeClass("playing");
    currentAudio = null;
  }
};

const playAudio = (src, button = null) => {
  stopAudio();
  const audio = new Audio(src);
  currentAudio = { audio, button };
  button?.addClass("playing");
  audio.addEventListener("ended", () => {
    if (currentAudio?.audio === audio) stopAudio();
  });
  audio.play().catch(stopAudio); // autoplay can be blocked until the user interacts
};

const scrollToBottom = () => {
  const chat = document.getElementById("chat-window");
  chat.scrollTop = chat.scrollHeight;
};

const createMessageLine = (type) => {
  const icon = $("<i class='fa'></i>").addClass(AVATAR_ICONS[type]);
  const avatar = $("<div class='avatar' aria-hidden='true'></div>").append(icon);
  $("#empty-state").addClass("hidden");
  return $("<div class='message-line'></div>").addClass(type).append(avatar);
};

// Text is always inserted with .text() so model output can never inject HTML
const appendMessage = (text, type, audioSrc = null) => {
  const line = createMessageLine(type).append($("<div class='message-box'></div>").text(text));

  if (audioSrc) {
    const button = $(
      "<button type='button' class='replay-button' aria-label='Play audio' title='Play audio'><i class='fa fa-volume-up'></i></button>"
    );
    button.on("click", () => playAudio(audioSrc, button));
    line.append(button);
  }

  $("#message-list").append(line);
  scrollToBottom();
  return line;
};

const showTyping = (type) => {
  const line = createMessageLine(type)
    .addClass("typing")
    .append("<div class='message-box'><span class='dot'></span><span class='dot'></span><span class='dot'></span></div>");
  $("#message-list").append(line);
  scrollToBottom();
  return line;
};

const setBusy = (value) => {
  busy = value;
  $("#message-input, #send-button, .suggestion").prop("disabled", value);
  if (!value) $("#message-input").trigger("focus");
};

const updateSendButton = () => {
  if (recording) return;
  const hasText = $("#message-input").val().trim() !== "";
  $("#send-button")
    .toggleClass("send", hasText)
    .attr("aria-label", hasText ? "Send message" : "Record a voice message")
    .attr("title", hasText ? "Send message" : "Record a voice message")
    .find("i")
    .attr("class", hasText ? "fa fa-paper-plane" : "fa fa-microphone");
};

const askAssistant = async (message) => {
  const typing = showTyping("bot");
  try {
    const response = await processUserMessage(message);
    const audioSrc = "data:audio/wav;base64," + response.aiResponseSpeech;
    typing.remove();
    const line = appendMessage(response.aiResponseText, "bot", audioSrc);
    playAudio(audioSrc, line.find(".replay-button"));
  } catch (error) {
    typing.remove();
    appendMessage(error.message, "error");
  } finally {
    setBusy(false);
  }
};

const sendTextMessage = (text) => {
  const message = cleanTextInput(text);
  if (!message || busy || recording) return;

  $("#message-input").val("");
  updateSendButton();
  setBusy(true);
  appendMessage(message, "user");
  askAssistant(message);
};

const formatTime = (seconds) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

const startRecording = async () => {
  stopAudio();
  try {
    recorder = await recordAudio();
  } catch (error) {
    appendMessage("Microphone access is required to record your voice.", "error");
    return;
  }
  recorder.start();
  recording = true;

  let seconds = 0;
  $("#message-input").prop("disabled", true);
  $("#send-button")
    .addClass("recording")
    .attr("aria-label", "Stop recording")
    .attr("title", "Stop recording")
    .find("i")
    .attr("class", "fa fa-stop");
  $("#recording-timer").text(formatTime(seconds));
  $("#recording-bar").removeClass("hidden");

  recordingTimer = setInterval(() => {
    seconds += 1;
    $("#recording-timer").text(formatTime(seconds));
    if (seconds >= MAX_RECORDING_SECONDS) stopRecording();
  }, 1000);
};

const stopRecording = async () => {
  if (!recording) return;
  recording = false;
  clearInterval(recordingTimer);
  $("#recording-bar").addClass("hidden");
  $("#send-button").removeClass("recording");
  updateSendButton();
  setBusy(true);

  const userRecording = await recorder.stop();
  const typing = showTyping("user");
  try {
    const userMessage = await getSpeechToText(userRecording);
    typing.remove();
    appendMessage(userMessage, "user", userRecording.audioUrl);
    await askAssistant(userMessage);
  } catch (error) {
    typing.remove();
    appendMessage(error.message, "error");
    setBusy(false);
  }
};

const applyTheme = (dark) => {
  $("body").toggleClass("dark-mode", dark);
  $("#theme-toggle i").attr("class", dark ? "fa fa-sun-o" : "fa fa-moon-o");
};

$(function () {
  const savedTheme = localStorage.getItem(THEME_KEY);
  applyTheme(savedTheme ? savedTheme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches);

  $("#theme-toggle").on("click", () => {
    const dark = !$("body").hasClass("dark-mode");
    applyTheme(dark);
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  });

  $("#message-input").on("input", updateSendButton);

  $("#chat-form").on("submit", (event) => {
    event.preventDefault();
    sendTextMessage($("#message-input").val());
  });

  $("#send-button").on("click", () => {
    if (recording) {
      stopRecording();
    } else if ($("#send-button").hasClass("send")) {
      sendTextMessage($("#message-input").val());
    } else if (!busy) {
      startRecording();
    }
  });

  $(".suggestion").on("click", function () {
    sendTextMessage($(this).text());
  });
});
