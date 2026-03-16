// recall_voice_inject.js

const fs = require("fs");
const fetch = require("node-fetch");

const RECALL_API_KEY = "d4911fcff4042cfe780202f45c7361b4cbf542b4";
const BOT_ID = "d312e185-8432-40a7-9632-8561a5c6e591";

// load mp3 file
const audioBuffer = fs.readFileSync("voice1.mp3");

// convert to base64
const base64Audio = audioBuffer.toString("base64");

async function injectVoice() {

  const res = await fetch(
    `https://ap-northeast-1.recall.ai/api/v1/bot/${BOT_ID}/output_audio/`,
    {
      method: "POST",
      headers: {
        "Authorization": RECALL_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        kind: "mp3",
        b64_data: base64Audio
      })
    }
  );

  const data = await res.json();

  console.log("Voice sent:", data);
}

injectVoice();