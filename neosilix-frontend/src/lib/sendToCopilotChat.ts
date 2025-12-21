export async function sendToCopilotChat(prompt: string) {
  try {
    const res = await fetch("http://localhost:5000/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt })
    });

    if (!res.ok) {
      throw new Error("Failed to fetch AI response");
    }

    const data = await res.json();
    return data.reply;
  } catch (err) {
    console.error("Chat error:", err);
    return "Sorry, I couldn’t process that. Try again.";
  }
}
