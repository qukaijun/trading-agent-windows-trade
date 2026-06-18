import os
from io import BytesIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new(interchange_level=1, joliet=True)

src = r"E:\投资工具\trading-agent-windows-mvp\release\TradingAgentAssistant-Setup-0.2.2-p0-candidate-20260613.exe"
iso.add_file(src, "/TAA_022.EXE;1", joliet_path="/TradingAgentAssistant-0.2.2.exe")

readme_content = b"TradingAgents P0 0.2.2\r\nDouble-click TAA_022.EXE to install.\r\n"
iso.add_fp(BytesIO(readme_content), len(readme_content), "/README.TXT;1", joliet_path="/README.TXT")

out = r"E:\投资工具\trading-agent-windows-mvp\vm-transfer\TradingAgents-0.2.2.iso"
iso.write(out)
iso.close()
sz = os.path.getsize(out)
print(f"ISO: {out}")
print(f"Size: {sz} bytes ({sz/1024/1024:.1f} MB)")
