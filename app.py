from flask import Flask, request, jsonify, render_template_string, send_from_directory
import yt_dlp
import threading
import os
import uuid
import glob

app = Flask(__name__)

DOWNLOADS = "downloads"
os.makedirs(DOWNLOADS, exist_ok=True)

progress_data = {}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>SaqiDownloader</title>

<style>

body{
    background:#0f0f0f;
    color:white;
    font-family:Arial;
    margin:0;
    padding:20px;
}

.container{
    max-width:700px;
    margin:auto;
}

h1{
    text-align:center;
    margin-bottom:20px;
}

.inputBox{
    display:flex;
    gap:10px;
}

input{
    flex:1;
    padding:14px;
    border:none;
    border-radius:12px;
    background:#1f1f1f;
    color:white;
    font-size:16px;
}

button{
    padding:14px 18px;
    border:none;
    border-radius:12px;
    background:#ff0033;
    color:white;
    font-size:15px;
    font-weight:bold;
    cursor:pointer;
}

button:disabled{
    opacity:0.5;
    cursor:not-allowed;
}

.video{
    background:#1a1a1a;
    border-radius:15px;
    overflow:hidden;
    margin-top:20px;
}

.thumb{
    width:100%;
}

.info{
    padding:15px;
}

.title{
    font-size:18px;
    font-weight:bold;
    margin-bottom:10px;
}

select{
    width:100%;
    padding:12px;
    border:none;
    border-radius:10px;
    background:#2a2a2a;
    color:white;
    margin-bottom:10px;
}

.progress{
    width:100%;
    height:10px;
    background:#333;
    border-radius:50px;
    overflow:hidden;
    margin-top:10px;
}

.bar{
    width:0%;
    height:100%;
    background:#00ff88;
    transition:width .3s;
}

.percent{
    margin-top:10px;
    font-size:18px;
    font-weight:bold;
    text-align:center;
}

.openBtn{
    display:none;
    width:100%;
    margin-top:10px;
    text-decoration:none;
    text-align:center;
    background:#00aa55;
    padding:14px;
    border-radius:10px;
    color:white;
    font-weight:bold;
}

</style>
</head>

<body>

<div class="container">

<h1>SaqiDownloader</h1>

<div class="inputBox">

<input type="text" id="url"
placeholder="Paste YouTube video or playlist link">

<button id="searchBtn" onclick="searchVideo()">
Search
</button>

</div>

<div id="videos"></div>

</div>

<script>

async function searchVideo(){

    let url = document.getElementById("url").value.trim();

    if(!url) return;

    let btn = document.getElementById("searchBtn");

    btn.disabled = true;
    btn.innerText = "Searching...";

    document.getElementById("videos").innerHTML = "";

    try{

        const res = await fetch("/info",{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({url:url})
        });

        const data = await res.json();

        btn.disabled = false;
        btn.innerText = "Search";

        data.videos.forEach((video,index)=>{

            let qualities = "";

            video.qualities.forEach(q=>{
                qualities += `
                <option value="${q}">
                    ${q}p
                </option>
                `;
            });

            document.getElementById("videos").innerHTML += `

            <div class="video">

                <img class="thumb" src="${video.thumbnail}">

                <div class="info">

                    <div class="title">
                        ${video.title}
                    </div>

                    <select id="quality_${index}">
                        ${qualities}
                    </select>

                    <button id="downloadBtn_${index}"
                    onclick="downloadVideo('${video.url}',${index})">

                    Download

                    </button>

                    <div class="progress">
                        <div class="bar" id="bar_${index}"></div>
                    </div>

                    <div class="percent" id="percent_${index}">
                        0%
                    </div>

                    <a class="openBtn"
                    id="open_${index}"
                    target="_blank">

                    ▶ Open Video

                    </a>

                </div>

            </div>

            `;
        });

    }catch(e){

        btn.disabled = false;
        btn.innerText = "Search";

        alert(e);
    }
}

async function downloadVideo(url,index){

    let quality =
    document.getElementById("quality_"+index).value;

    let btn =
    document.getElementById("downloadBtn_"+index);

    btn.disabled = true;
    btn.innerText = "Downloading...";

    const res = await fetch("/download",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            url:url,
            quality:quality
        })
    });

    const data = await res.json();

    checkProgress(data.id,index,btn);
}

function checkProgress(id,index,btn){

    let interval = setInterval(async()=>{

        const res =
        await fetch("/progress/"+id);

        const data =
        await res.json();

        let percent =
        parseFloat(data.percent || 0);

        if(percent > 100) percent = 100;

        document.getElementById("bar_"+index)
        .style.width = percent + "%";

        document.getElementById("percent_"+index)
        .innerText = percent.toFixed(1) + "%";

        if(data.status == "finished"){

            clearInterval(interval);

            document.getElementById("bar_"+index)
            .style.width = "100%";

            document.getElementById("percent_"+index)
            .innerText = "Download Complete";

            btn.innerText = "Downloaded";

            let openBtn =
            document.getElementById("open_"+index);

            openBtn.style.display = "block";

            openBtn.href = "/file/" + data.file;
        }

    },500);
}

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/info", methods=["POST"])
def info():

    url = request.json["url"]

    ydl_opts = {
        "quiet": True,
        "extract_flat": False
    }

    videos = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        data = ydl.extract_info(url, download=False)

        entries = data.get("entries")

        if entries:

            for entry in entries:

                if not entry:
                    continue

                qualities = []

                for f in entry.get("formats", []):

                    h = f.get("height")

                    if h and h not in qualities:
                        qualities.append(h)

                qualities.sort(reverse=True)

                videos.append({
                    "title": entry.get("title"),
                    "thumbnail": entry.get("thumbnail"),
                    "url": entry.get("webpage_url"),
                    "qualities": qualities
                })

        else:

            qualities = []

            for f in data.get("formats", []):

                h = f.get("height")

                if h and h not in qualities:
                    qualities.append(h)

            qualities.sort(reverse=True)

            videos.append({
                "title": data.get("title"),
                "thumbnail": data.get("thumbnail"),
                "url": url,
                "qualities": qualities
            })

    return jsonify({
        "videos": videos
    })

@app.route("/download", methods=["POST"])
def download():

    url = request.json["url"]

    quality = request.json["quality"]

    download_id = uuid.uuid4().hex

    progress_data[download_id] = {
        "percent": 0,
        "status": "downloading",
        "file": ""
    }

    def hook(d):

        if d["status"] == "downloading":

            downloaded =
            d.get("downloaded_bytes",0)

            total =
            d.get("total_bytes") or
            d.get("total_bytes_estimate") or 1

            percent =
            (downloaded / total) * 100

            progress_data[download_id]["percent"] = percent

        elif d["status"] == "finished":

            filename =
            os.path.basename(d["filename"])

            progress_data[download_id]["percent"] = 100
            progress_data[download_id]["status"] = "finished"
            progress_data[download_id]["file"] = filename

    ydl_opts = {

        "format":
        f"bestvideo[height<={quality}]+bestaudio/best",

        "outtmpl":
        f"{DOWNLOADS}/%(title)s.%(ext)s",

        "merge_output_format":"mp4",

        "progress_hooks":[hook],

        "quiet":True
    }

    def run():

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    threading.Thread(target=run).start()

    return jsonify({
        "id":download_id
    })

@app.route("/progress/<id>")
def progress(id):

    return jsonify(
        progress_data.get(id,{
            "percent":0,
            "status":"downloading"
        })
    )

@app.route("/file/<path:filename>")
def file(filename):

    return send_from_directory(
        DOWNLOADS,
        filename,
        as_attachment=False
    )
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
