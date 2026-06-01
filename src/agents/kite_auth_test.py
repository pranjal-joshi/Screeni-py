"""
Interactive Kite auth + agent query script.
Run with: uv run python src/agents/kite_auth_test.py
"""
import sys, os, re, logging, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
logging.basicConfig(level=logging.WARNING)
warnings.filterwarnings('ignore')

from agents.kite_session import get_or_create_session
from agents.agent_loader import AgentLoader
from agents.screeni_agent import ScreeniAgent

print("Connecting to Kite MCP (session will stay open)...")
session = get_or_create_session()
print("Connected:", session.is_connected)

url_text = session.get_login_url()
url_match = re.search(r'https://kite\.zerodha\.com/connect/login\S+', url_text)
login_url = url_match.group(0) if url_match else url_text

print()
print("=" * 70)
print("KITE LOGIN URL (copy into browser):")
print(login_url)
print("=" * 70)
print()
print("The session is ALIVE. Log in to Zerodha in your browser, then come back here.")
input("Press ENTER after completing the login...")

print()
print("Building agent with live Kite session...")
loader = AgentLoader()
personas = loader.load_all()
persona = next((p for p in personas if 'Momentum' in p.get('name', '')), personas[0])
print(f"Using persona: {persona.get('name')}")

agent = ScreeniAgent(persona_config=persona)
# Override the agent's mcp_servers with our already-connected session server
try:
    agent._agent.mcp_servers = [session.server]
except Exception as e:
    print(f"Warning: could not attach live server to agent: {e}")

print("Running query inside the live Kite session...")
result = session.run_agent_query(agent._agent, "Top 3 stocks to trade tomorrow from Nifty 50")

print()
print("=" * 70)
print("AGENT RESULT:")
print("=" * 70)
print(result)
