"""Regenerate prototype Lucide vector assets. Run from the repo root with svglib and reportlab installed; see App/Lucide-LICENSE.txt."""
from pathlib import Path
from io import BytesIO
import json
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
icons={
'equal':'<line x1="5" x2="19" y1="9" y2="9"/><line x1="5" x2="19" y1="15" y2="15"/>',
'bell':'<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>',
'stop':'<rect width="18" height="18" x="3" y="3" rx="2" fill="black"/>',
'close':'<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
'paperclip':'<path d="m16 6-8.414 8.586a2 2 0 0 0 2.829 2.829l8.414-8.586a4 4 0 1 0-5.657-5.657l-8.379 8.551a6 6 0 1 0 8.485 8.485l8.379-8.551"/>',
'mic':'<path d="M12 19v3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><rect x="9" y="2" width="6" height="13" rx="3"/>',
'plus':'<path d="M5 12h14"/><path d="M12 5v14"/>',
'back':'<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
'search':'<path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/>',
'send':'<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>'}
base=Path('App/Assets.xcassets')
for name,markup in icons.items():
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="{2.5 if name=="plus" else 1.9}" stroke-linecap="round" stroke-linejoin="round">{markup}</svg>'
 folder=base/f'Room-{name}.imageset';folder.mkdir(exist_ok=True)
 renderPDF.drawToFile(svg2rlg(BytesIO(svg.encode())),str(folder/'icon.pdf'))
 (folder/'Contents.json').write_text(json.dumps({'images':[{'filename':'icon.pdf','idiom':'universal'}],'info':{'author':'xcode','version':1},'properties':{'preserves-vector-representation':True,'template-rendering-intent':'template'}},indent=2)+'\n')
