OpsWired autopilot - ONE-TIME setup (3 minutes), then nothing manual ever again.

1. Open Command Prompt and run:
     D:
     cd D:\bots
     git clone --branch autopilot --single-branch --depth 1 https://github.com/Kareem-Hany/opswired-media autopilot
     cd autopilot
     pip install gemini-webapi pillow "mcp<2"
2. Copy cookies.env.example to cookies.env and paste your two Gemini cookie values
   (never share this file or paste it in a chat; it is git-ignored and never uploaded).
3. Double-click start.bat and leave the window open.

From then on Claude drops a request file, your PC makes the images with your Gemini and pushes them back by itself.
If the window says "cookie error", paste fresh cookies into cookies.env and restart start.bat.
Needs: PC on, window open, Git able to push to GitHub (the same login you already use for Git).
