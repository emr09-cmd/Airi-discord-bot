export default function Home() {
  return (
    <main className="min-h-screen bg-[#1e1f22] text-[#dbdee1] flex items-center justify-center p-8">
      <div className="max-w-xl w-full bg-[#2b2d31] border border-[#3f4147] rounded-xl p-8 space-y-4">
        <h1 className="text-2xl font-bold text-white">🤖 Discord Bot Dashboard</h1>
        <p>
          The dashboard is written entirely in <b>Python</b> and runs inside your bot
          process on port <code className="bg-[#1e1f22] px-1.5 py-0.5 rounded">7131</code>.
        </p>
        <pre className="bg-[#1e1f22] rounded-lg p-4 text-sm overflow-x-auto">{`cd bot
pip install -r requirements.txt
cp .env.example .env   # add DISCORD_BOT_TOKEN + DASHBOARD_PASSWORD
python run.py`}</pre>
        <p>
          Then open{" "}
          <a className="text-[#00a8fc] underline" href="http://localhost:7131">
            http://localhost:7131
          </a>
          . See <code>bot/README.md</code> for details.
        </p>
      </div>
    </main>
  );
}
