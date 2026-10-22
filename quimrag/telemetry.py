def stats(e):
 d={"Device":e.dev,"Embedding backend":e.backend,"Documents":str(len(e.documents)),"Chunks":str(len(e.chunks))}
 try:
  import psutil
  d["CPU usage"]=f"{psutil.cpu_percent(interval=.1):.0f}%";d["RAM usage"]=f"{psutil.virtual_memory().percent:.0f}%";d["Process RAM"]=f"{psutil.Process().memory_info().rss/1048576:.0f} MB"
 except Exception:d["Telemetry"]="Install psutil"
 return d
