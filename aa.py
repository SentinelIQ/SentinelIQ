#!/usr/bin/env python3
from datetime import datetime
import os, pandas as pd
from pymisp import PyMISP

URL, KEY = os.environ['MISP_URL'], os.environ['MISP_KEY']
misp = PyMISP(URL, KEY, ssl=False)           # ✅ deixe True em produção

IOC_VALUE = "bolepaund.com"

# 1) Busca o atributo que tem exatamente esse value
raw = misp.search(
    'attributes',
    value=IOC_VALUE,
    pythonify=False,
    metadata=True,            # garante bloco Event
    include_event_info=True,
    include_event_tags=True,
    include_correlations=True,
    include_context=True,
)

attrs = raw['Attribute'] if isinstance(raw, dict) else raw
if not attrs:
    print(f"Nenhum atributo encontrado para {IOC_VALUE}")
    raise SystemExit()

# 2) Extrai IDs de evento
event_ids = {
    (a.get('Event') or {}).get('id', a.get('event_id'))
    for a in attrs
}
print(f"💡  {IOC_VALUE} aparece em {len(event_ids)} evento(s).")

# 3) Detalhes só desses eventos
events = misp.search(
    'events',
    eventid=list(event_ids),
    pythonify=False,
    include_galaxy=True,
    include_event_tags=True,
)

# 4) Timeline
# … (código de conexão e busca igual ao anterior) …

# 4) Timeline com URL
timeline = []
for ev in events:
    evt = ev['Event']
    ev_id = evt['id']
    # monta a URL de visualização
    url = f"{URL.rstrip('/')}/events/view/{ev_id}"
    timeline.append({
        "Event ID":    ev_id,
        "Date":        datetime.strptime(evt['date'], "%Y-%m-%d"),
        "Info":        evt['info'],
        "Tags":        ", ".join(t['name'] for t in evt.get('Tag', [])),
        "URL":         url,
    })

df = pd.DataFrame(timeline).sort_values('Date')
print("\nTimeline:")
print(df.to_string(index=False))

