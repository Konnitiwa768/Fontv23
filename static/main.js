const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
ctx.lineWidth = 4;
ctx.lineCap = "round";

let drawing = false;

function getXY(e) {
  const rect = canvas.getBoundingClientRect();
  if (e.touches) {
    return [e.touches[0].clientX - rect.left, e.touches[0].clientY - rect.top];
  } else {
    return [e.clientX - rect.left, e.clientY - rect.top];
  }
}

function start(e) {
  drawing = true;
  const [x, y] = getXY(e);
  ctx.beginPath();
  ctx.moveTo(x, y);
  e.preventDefault();
}

function move(e) {
  if (!drawing) return;
  const [x, y] = getXY(e);
  ctx.lineTo(x, y);
  ctx.stroke();
  e.preventDefault();
}

function end(e) {
  drawing = false;
  e.preventDefault();
}

canvas.addEventListener('mousedown', start);
canvas.addEventListener('mousemove', move);
canvas.addEventListener('mouseup', end);
canvas.addEventListener('touchstart', start);
canvas.addEventListener('touchmove', move);
canvas.addEventListener('touchend', end);

function saveGlyph() {
  const char = document.getElementById('char').value;
  if (!char || char.length !== 1) {
    alert("1文字を入力してください");
    return;
  }
  const img = canvas.toDataURL("image/png");
  fetch("/save_glyph", {
    method: "POST",
    body: new URLSearchParams({ char, image: img })
  }).then(() => {
    log("保存しました");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });
}

function buildFont() {
  fetch("/build_font").then(res => res.blob()).then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "myfont.ttf";
    a.click();
    log("フォントをビルドしました");
  });
}

function uploadFont() {
  fetch("/upload_font", { method: "POST" })
    .then(res => res.json())
    .then(res => {
      if (res.url) log("アップロード成功: " + res.url);
      else log("アップロード失敗");
    });
}

function log(msg) {
  document.getElementById("log").textContent = msg;
}
