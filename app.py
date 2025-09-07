import os
import time
import pandas as pd
from flask import (
    Flask, render_template_string, request, send_file, flash,
    send_from_directory, jsonify, redirect, url_for
)

# ===================== 설정 (환경변수 우선) =====================
SECRET_KEY = os.environ.get("SECRET_KEY", "change_me")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change_me")

# 무료 테스트: /opt/render/project/src/books_files
# 유료 + 디스크: /data/books_files
BOOKS_DIR = os.environ.get("BOOKS_DIR", "/opt/render/project/src/books_files")
os.makedirs(BOOKS_DIR, exist_ok=True)

IMAGE_BASENAME = "uploaded_img"  # uploaded_img.jpg / uploaded_img.png
ALLOWED_XLSX = {".xlsx"}
ALLOWED_IMG = {".jpg", ".jpeg", ".png"}

# ===================== Flask =====================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

# ===================== 템플릿 =====================
index_html = r'''
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>만화카페 도도 도서검색</title>
  <style>
    :root{
      /* 레이아웃 기본값 */
      --gap: clamp(14px, 2.6vw, 32px);
      --pad: clamp(16px, 3.2vw, 44px);
      --radius: clamp(16px, 3vw, 40px);

      /* 데스크톱 페이지 가로 폭: 80vw (≈ 20% 축소), 상한을 걸고 싶으면 min(80vw, 1400px) */
      --page-width: min(80vw, 1400px);

      /* 상하 여백 */
      --page-vmargin: clamp(10px, 3.4vh, 28px);

      /* 높이 기준 */
      --img-h: clamp(340px, 47vh, 640px);

      --h1: clamp(1.8rem, 2.6vw, 2.5rem);
      --text: clamp(1.04rem, 1.15vw, 1.18rem);
      --btn-fz: clamp(1.02rem, 1.15vw, 1.2rem);
      --btn-py: clamp(10px, 1.3vw, 16px);
      --btn-px: clamp(20px, 2.2vw, 38px);
      --input-fz: clamp(1.05rem, 1.2vw, 1.22rem);
      --input-pd: clamp(10px, 1.4vw, 16px);
      --max-input: 680px;
    }

    body{
      background:linear-gradient(135deg,#e0f7fa 60%,#f8bbd0 100%);
      font-family:'Noto Sans KR',sans-serif;
      margin:0; min-height:100vh;
    }
    .flex-wrap{
      display:flex; justify-content:center; align-items:stretch;
      width: var(--page-width);                  /* 데스크톱 기본: 80vw */
      margin:var(--page-vmargin) auto;
      gap:var(--gap);
    }

    /* 높이(검색 전에도 충분히 크게 보이도록): 83vh 기준 */
    .container{
      padding:var(--pad);
      min-height: max(var(--img-h), calc(83vh - (var(--page-vmargin) * 2)));
      padding-bottom: var(--pad); /* 하단 버튼 공간 */

      border-radius:var(--radius); background:white;
      box-shadow:0 10px 56px #b2dfdb80; text-align:center;
      border:2px solid #00bfae20; display:flex; flex-direction:column;
    }
    .imgbox{
      background:rgba(255,255,255,0.90); border-radius:var(--radius);
      box-shadow:0 10px 56px #b2dfdb30; display:flex; align-items:center; justify-content:center;
      padding:22px 18px; margin:0;
      min-height: max(var(--img-h), calc(83vh - (var(--page-vmargin) * 2)));
    }
.imgbox img {
    width: 90%;
    height: 90%;
    object-fit: cover; /* 비율 유지하며 꽉 채움, 일부 잘릴 수 있음 */
    border-radius: 32px;
    box-shadow: 0 2px 18px #b2dfdb40;
}
    h1{ color:#00695c; font-size:var(--h1); font-weight:bold; margin-bottom:16px; letter-spacing:-1px; }

    /* 폼/입력 중앙 정렬 */
    form{
      margin-bottom:10px;
      display:flex; flex-direction:column; align-items:center; gap:10px;
    }
    input[type="text"]{
      display:block;
      width:min(var(--max-input), 96%);
      max-width:var(--max-input);
      margin:0 auto;
      font-size:var(--input-fz);
      padding:var(--input-pd);
      border-radius:16px;
      border:1.8px solid #b2dfdb;
      box-sizing:border-box;
      text-align:left;
    }
    button{
      padding:var(--btn-py) var(--btn-px);
      margin:10px; border-radius:18px; background:#00bfae; color:white; border:none;
      cursor:pointer; font-weight:bold; font-size:var(--btn-fz);
      transition:0.18s; box-shadow:0 2px 12px #00bfae20;
      align-self:center;
    }
    button:hover{ background:#00acc1; }
    .result-box{ margin-top:22px;}
    table{
      width:100%; border-collapse:separate; border-spacing:0 10px;
      font-size:var(--text);
    }
    th, td{
      border:1.8px solid #b2dfdb; padding:12px 12px; border-radius:14px; background:white;
    }
    th{ background:#00bfae; color:white; font-weight:700; }
    tr:nth-child(even) td{ background:#f0f5f5; }

    /* 하단 링크: 흰 배경 내부 거의 바닥 */
    .container-footer{
      margin-top:auto;
      padding-top:16px;
    }
    .linklike{
      background:none; border:none; color:#00bfae; cursor:pointer;
      text-decoration:underline; font-weight:600; font-size:1rem; font-family:inherit;
      padding:0; transition:none;
      text-shadow:none; box-shadow:none; outline:none; -webkit-tap-highlight-color: transparent;
      filter:none; transform:none;
    }
    .linklike:hover{
      background:none !important; color:#00bfae; text-decoration:underline;
      text-shadow:none; box-shadow:none; filter:none; transform:none;
    }

    /* ===== 데스크톱: 좌우 정확히 5:5 (그대로 유지) ===== */
    @media (min-width: 901px){
      .flex-wrap{
        flex-direction: row;     
        flex-wrap: nowrap;       
      }
      .container,
      .imgbox{
        flex: 0 0 50%;   /* 50% 고정 */
        width: 50%;
        min-width: 0;
        max-width: none;
      }
    }

    /* ===== 모바일 & 포트레이트(세로)에서: 위/아래 스택 + 보기 좋은 높이 ===== */
    /* 1) 전형적 모바일 너비 */
    @media (max-width: 900px){
      .flex-wrap{
        flex-direction:column; 
        align-items:center; 
        gap: 14px; 
        margin: 8px auto;
        width: min(94vw, 680px);   /* 모바일은 약간 더 좁게 */
      }
      .container, .imgbox{ width: 100%; flex: 1 1 auto; }

      /* 보기 좋은 평균 높이: 합쳐도 1 스크린 남짓 */
      .container{
        min-height: clamp(360px, 52svh, 620px);
        padding: 18px;
        padding-bottom: 18px;
      }
      .imgbox{
        min-height: clamp(220px, 40svh, 520px);
        padding: 14px;
      }
      .container-footer{
        margin-top:auto;
        padding-top: 12px;
      }
    }
    /* 2) 태블릿 등 가로폭은 넓어도 '세로로 들었을 때' */
    @media (orientation: portrait) and (max-width: 1200px){
      .flex-wrap{
        flex-direction:column; 
        align-items:center; 
        gap: 14px; 
        margin: 8px auto;
        width: min(94vw, 900px);   /* 태블릿 세로는 살짝 더 넓게 */
      }
      .container, .imgbox{ width: 100%; flex: 1 1 auto; }
      .container{
        min-height: clamp(380px, 52svh, 640px);
        padding: 18px;
        padding-bottom: 18px;
      }
      .imgbox{
        min-height: clamp(240px, 40svh, 560px);
        padding: 14px;
      }
    }

    /* svh 미지원 폴백 (모바일 & 포트레이트) */
    @supports not (height: 1svh) {
      @media (max-width: 900px){
        .container{ min-height: clamp(360px, 52vh, 620px); }
        .imgbox{ min-height: clamp(220px, 40vh, 520px); }
      }
      @media (orientation: portrait) and (max-width: 1200px){
        .container{ min-height: clamp(380px, 52vh, 640px); }
        .imgbox{ min-height: clamp(240px, 40vh, 560px); }
      }
    }
  </style>
</head>
<body>
  <div class="flex-wrap">
    <div class="container">
      <h1><span translate="no">만화카페 도도 도서검색</span></h1>

      <form method="post">
        <input type="text" name="keyword" placeholder="제목, 최종권수, 저자, ISBN, 위치 검색" autofocus required>
        <button type="submit">검색</button>
      </form>

      {% if error_msg %}
        <div style="color:red;font-weight:bold;margin:18px 0 8px 0;">{{ error_msg }}</div>
      {% endif %}
      {% if results %}
      <div class="result-box">
        <table>
          <tr><th>제목</th><th>최종권수</th><th>저자</th><th>ISBN</th><th>위치</th></tr>
          {% for book in results %}
          <tr>
            <td>{{ book['제목'] }}</td>
            <td>{{ book['최종권수'] }}</td>
            <td>{{ book['저자'] }}</td>
            <td>{{ book['ISBN'] }}</td>
            <td>{{ book['위치'] }}</td>
          </tr>
          {% endfor %}
        </table>
      </div>
      {% endif %}
      {% if no_result %}
        <div style="color:#666;font-size:2em;margin-top:18px;">아직 준비되지 않은 도서 입니다</div>
      {% endif %}

      <!-- 흰 배경 내부 바닥 근처 -->
      <div class="container-footer">
        <button type="button" class="linklike" onclick="showPwModal();return false;">관리자/도서업데이트</button>
      </div>

      <!-- 비번 팝업 -->
      <div id="pwModal" style="display:none; position:fixed; left:0; top:0; width:100vw; height:100vh; background:rgba(0,0,0,0.21); z-index:9999; justify-content:center; align-items:center;">
        <div class="modal-inner" style="background:white; padding:24px 28px 18px 28px; border-radius:18px; min-width:320px; box-shadow:0 4px 30px #0001; text-align:center; position:relative">
          <div style="font-size:1.05rem;font-weight:700;margin-bottom:10px;color:#00695c;">관리자 비밀번호</div>
          <form id="pwForm" method="post" action="/dodo-manager">
            <input type="password" name="password" placeholder="비밀번호" required style="padding:10px 14px; border:1.2px solid #b2dfdb; border-radius:10px; width:80%; box-sizing:border-box;">
            <input type="hidden" name="action" value="login">
            <div class="btn-row" style="display:flex; gap:10px; justify-content:center; align-items:center; margin-top:10px;">
              <button type="submit" class="btn" style="background:#00bfae; color:white; padding:8px 14px; border-radius:10px; font-weight:600; font-size:1rem; border:none; cursor:pointer">확인</button>
              <button type="button" class="btn cancel" onclick="hidePwModal()" style="background:#eee; color:#666; padding:8px 14px; border-radius:10px; font-weight:600; font-size:1rem; border:none; cursor:pointer">취소</button>
            </div>
          </form>
          <span class="close-x" onclick="hidePwModal()" style="position:absolute; top:7px; right:13px; font-size:1.45em; cursor:pointer; color:#ccc;">×</span>
        </div>
      </div>

      <script>
        function showPwModal(){ document.getElementById('pwModal').style.display='flex'; }
        function hidePwModal(){ document.getElementById('pwModal').style.display='none'; }
        document.addEventListener('DOMContentLoaded', function(){
          const pwForm = document.getElementById('pwForm');
          if(pwForm){ pwForm.addEventListener('submit', function(){ hidePwModal(); }); }
        });
      </script>
    </div>

    <div class="imgbox">
      {% if img_exists %}
        <img src="/uploaded_img" alt="첨부 이미지">
      {% else %}
        <div style="color:#aaa;font-size:1.1em;">(아직 첨부된 이미지가 없습니다)</div>
      {% endif %}
    </div>
  </div>
</body>
</html>
'''

# 관리자 로그인
admin_login_html = r'''
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>관리자 로그인 | 만화카페 도도</title></head>
<body style="font-family:'Noto Sans KR',sans-serif; background:#f6fcf8;">
  <div style="max-width:520px;margin:80px auto;background:#fff;padding:28px;border-radius:16px;box-shadow:0 8px 24px #00000014;text-align:center">
    <h2 style="color:#00bfae;margin-top:0">관리자 로그인</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul style="list-style:none;padding:0">
          {% for category, message in messages %}
            <li style="color:{{ 'green' if category=='success' else 'red' }};">{{ message }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post" action="/dodo-manager">
      <input type="password" name="password" placeholder="관리자 비밀번호" required
             style="padding:12px;border:1px solid #b2dfdb;border-radius:10px;width:72%">
      <input type="hidden" name="action" value="login">
      <br><button type="submit"
             style="margin-top:12px;background:#00bfae;color:#fff;border:none;padding:10px 16px;border-radius:10px;font-weight:bold;cursor:pointer">
        로그인
      </button>
      <a href="/" style="margin-left:8px;color:#00bfae">← 검색 화면</a>
    </form>
  </div>
</body>
</html>
'''

# 관리자 페이지
admin_html = r'''
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"><title>도서관리 | 만화카페 도도</title>
  <style>
    body{background:#f6fcf8;font-family:'Noto Sans KR',sans-serif;}
    .container{max-width:1040px;margin:60px auto;padding:36px 44px 24px 44px;border-radius:44px;background:white;box-shadow:0 8px 32px #b2dfdb60;text-align:center;}
    h1{color:#00bfae;margin-bottom:24px;}
    input,button{padding:13px;margin:10px;border-radius:16px;border:1.5px solid #b2dfdb;}
    button{background:#00bfae;color:white;border:none;cursor:pointer;font-weight:bold;}
    button:hover{background:#00acc1;}
    ul.flash{list-style:none;padding:0;}
    li.success{color:green;} li.danger{color:red;}
    a{color:#00bfae;margin:0 8px;}
    .filelabel{font-size:1.09em;color:#009b7d;margin-top:14px;}
    #downloadModal{display:none;position:fixed;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.21);z-index:9999;justify-content:center;align-items:center;}
    #downloadModal .modal-inner{background:white;padding:32px 32px 20px 32px;border-radius:18px;min-width:340px;box-shadow:0 4px 30px #0001;text-align:center;position:relative;}
    #downloadModal .close-x{position:absolute;top:7px;right:13px;font-size:1.45em;cursor:pointer;color:#ccc;}
    #downloadModal button{background:#00bfae;color:white;padding:7px 20px;border-radius:10px;font-weight:bold;border:none;margin-top:12px;}
    #downloadModal button.cancel{background:#eee;color:#888;margin-left:7px;}
    #downloadModal ul{text-align:left;margin:10px auto;padding:0;max-height:300px;overflow:auto;}
    #downloadModal li{margin:5px 0;list-style:none;display:flex;align-items:center;justify-content:space-between;}
    #downloadModal .filename{max-width:360px;overflow:hidden;text-overflow:ellipsis;}
    #downloadModal .download-btn{background:#00796b;font-size:0.97em;}
    #downloadModal .delete-btn{background:#c62828;color:white;font-size:0.97em;}
    #status{margin-top:8px;color:#c62828;font-size:0.95em;}

    .linklike{
      background:none; border:none; color:#00bfae; cursor:pointer;
      text-decoration:underline; font-weight:600; font-size:1rem; font-family:inherit;
      padding:0; transition:none; text-shadow:none; box-shadow:none; outline:none; -webkit-tap-highlight-color:transparent;
    }
    .linklike:hover{ background:none!important; color:#00bfae; text-decoration:underline; text-shadow:none; box-shadow:none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>도서 데이터 업로드 (관리자)</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
      <ul class="flash">
        {% for category, message in messages %}
          <li class="{{ category }}">{{ message }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    {% endwith %}

    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="password" value="{{ admin_pw }}">
      <input type="file" name="file" accept=".xlsx" required>
      <button type="submit" name="action" value="books">도서 업로드</button>
    </form>

    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="password" value="{{ admin_pw }}">
      <span class="filelabel">우측 이미지 업로드 (jpg/png만, 최대 1장)</span><br>
      <input type="file" name="imgfile" accept=".jpg,.jpeg,.png" required>
      <button type="submit" name="action" value="image">이미지 업로드</button>
    </form>

    <div style="margin-top:22px;">
      <button id="openDownload" type="button" class="linklike">기존 도서 데이터 다운로드/삭제</button>
      <a href="/" class="linklike">검색 화면으로</a>
      <div id="status"></div>
    </div>

    <div id="downloadModal">
      <div class="modal-inner">
        <div style="font-size:1.09em;font-weight:bold;margin-bottom:12px;">도서 데이터 파일 목록</div>
        <ul id="fileList"><li>불러오는 중...</li></ul>
        <button class="cancel" onclick="hideDownloadModal()">닫기</button>
        <span class="close-x" onclick="hideDownloadModal()">×</span>
      </div>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', function () {
      var btn = document.getElementById('openDownload');
      if (btn) {
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          showDownloadModal();
        });
      }
    });

    function showDownloadModal(){
      document.getElementById('downloadModal').style.display='flex';
      loadFileList();
    }
    function hideDownloadModal(){ document.getElementById('downloadModal').style.display='none'; }
    function setStatus(msg){ var s=document.getElementById('status'); if(s){ s.textContent=msg||''; } }

    function loadFileList(){
      setStatus('');
      fetch('/filelist?pw={{ admin_pw }}')
        .then(function(r){ if(!r.ok){ setStatus('목록 로드 실패: '+r.status); } return r.json(); })
        .then(function(data){
          var ul=document.getElementById('fileList');
          if(!data){ ul.innerHTML='<li>오류: 응답 없음</li>'; return; }
          if(data.error){ ul.innerHTML='<li>'+ (data.error || '오류') +'</li>'; return; }
          if(!data.files || data.files.length==0){ ul.innerHTML='<li>파일이 없습니다</li>'; return; }
          ul.innerHTML='';
          data.files.forEach(function(file){
            var li=document.createElement('li');
            var nameSpan=document.createElement('span'); nameSpan.className='filename'; nameSpan.textContent=file;
            var dBtn=document.createElement('button'); dBtn.className='download-btn'; dBtn.textContent='डाउन로드'; dBtn.addEventListener('click', function(){ downloadFile(file); });
            var delBtn=document.createElement('button'); delBtn.className='delete-btn'; delBtn.textContent='삭제'; delBtn.addEventListener('click', function(){ deleteFile(file); });
            li.appendChild(nameSpan); li.appendChild(dBtn); li.appendChild(delBtn); ul.appendChild(li);
          });
        })
        .catch(function(err){ setStatus('목록 로드 오류: ' + (err && err.message ? err.message : err)); });
    }

    function downloadFile(fname){
      setStatus('');
      const url = '/download/' + encodeURIComponent(fname) + '?pw={{ admin_pw }}';
      fetch(url)
        .then(function(resp){
          if(!resp.ok){ setStatus('다운로드 실패: ' + resp.status); return null; }
          return resp.blob().then(function(blob){
            const a=document.createElement('a'); const objectUrl=URL.createObjectURL(blob);
            a.href=objectUrl; a.download=fname; document.body.appendChild(a); a.click(); URL.revokeObjectURL(objectUrl); a.remove();
          });
        })
        .catch(function(err){ setStatus('다운로드 오류: ' + (err && err.message ? err.message : err)); });
    }

    function deleteFile(fname){
      setStatus('');
      if(!confirm(fname+' 파일을 삭제하시겠습니까?')) return;
      fetch('/deletefile/'+encodeURIComponent(fname)+'?pw={{ admin_pw }}', {method:'POST'})
        .then(function(r){ if(!r.ok){ setStatus('삭제 실패: '+r.status); return null; } return r.json(); })
        .then(function(data){ if(!data) return; if(data.success){ loadFileList(); } else{ setStatus(data.msg || '삭제 실패'); } })
        .catch(function(err){ setStatus('삭제 오류: ' + (err && err.message ? err.message : err)); });
    }
  </script>
</body>
</html>
'''

# ===================== 유틸 =====================
def latest_books_file():
    files = [f for f in os.listdir(BOOKS_DIR) if f.endswith(".xlsx")]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(BOOKS_DIR, files[0])

def read_books():
    latest_file = latest_books_file()
    if not latest_file:
        raise FileNotFoundError("업로드된 도서 데이터가 없습니다!")

    df = pd.read_excel(latest_file, dtype={'ISBN': str})

    required = ["제목", "최종권수", "저자", "ISBN", "위치"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"엑셀에 {missing} 컬럼이 없습니다!")

    df = df.fillna('')
    df = df.applymap(lambda x: '' if (isinstance(x, str) and x.strip().lower() in ('nan','none','null')) else x)

    def clean_int_like(x):
        if x == '' or x is None: return ''
        s = str(x).strip()
        try:
            f = float(s)
            return str(int(f)) if f.is_integer() else s
        except (ValueError, TypeError):
            return s

    for col in ['최종권수', '위치']:
        if col in df.columns:
            df[col] = df[col].apply(clean_int_like)

    return df

def allowed_ext(filename, allow_set):
    ext = os.path.splitext(filename)[1].lower()
    return ext in allow_set

def current_image_path():
    for ext in [".jpg", ".jpeg", ".png"]:
      p = os.path.join(BOOKS_DIR, IMAGE_BASENAME + ext)
      if os.path.exists(p):
          return p
    return None

def unique_filename(directory: str, original_name: str) -> str:
    base_name = os.path.basename(original_name)
    name, ext = os.path.splitext(base_name)
    candidate = base_name
    idx = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{name}_{idx}{ext}"
        idx += 1
    return candidate

# ===================== 라우트 =====================
@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    img_exists = current_image_path() is not None
    error_msg = None
    no_result = False
    if request.method == "POST":
        keyword = request.form["keyword"]
        try:
            df = read_books()
            results = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)].to_dict("records")
            if len(results) == 0:
                no_result = True
        except FileNotFoundError:
            error_msg = "업로드된 도서 데이터가 없습니다. 관리자에게 문의해 주세요."
        except ValueError as e:
            error_msg = str(e)
    return render_template_string(index_html, results=results, img_exists=img_exists, error_msg=error_msg, no_result=no_result)

@app.route("/dodo-manager", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and request.form.get("action") == "login":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            return render_template_string(admin_html, admin_pw=pw)
        else:
            flash("비밀번호가 틀렸습니다.", "danger")
            return render_template_string(admin_login_html)

    if request.method == "GET":
        return render_template_string(admin_login_html)

    action = request.form.get("action")
    pw = request.form.get("password", "")
    if pw != ADMIN_PASSWORD:
        flash("권한이 없습니다. 다시 로그인해 주세요.", "danger")
        return redirect(url_for("admin"))

    if action == "books":
        file = request.files.get("file")
        if file and allowed_ext(file.filename, ALLOWED_XLSX):
            os.makedirs(BOOKS_DIR, exist_ok=True)
            final_name = unique_filename(BOOKS_DIR, file.filename)
            file.save(os.path.join(BOOKS_DIR, final_name))
            flash("도서 데이터가 성공적으로 업로드되었습니다!", "success")
        else:
            flash("올바른 엑셀 파일(.xlsx)만 업로드 가능합니다.", "danger")

    elif action == "image":
        imgfile = request.files.get("imgfile")
        if imgfile and allowed_ext(imgfile.filename, ALLOWED_IMG):
            for e in [".jpg", ".jpeg", ".png"]:
                old = os.path.join(BOOKS_DIR, IMAGE_BASENAME + e)
                if os.path.exists(old):
                    try: os.remove(old)
                    except: pass
            ext = os.path.splitext(imgfile.filename)[1].lower()
            imgfile.save(os.path.join(BOOKS_DIR, IMAGE_BASENAME + ext))
            flash("이미지가 성공적으로 업로드되었습니다!", "success")
        else:
            flash("올바른 이미지 파일(jpg/png)만 업로드 가능합니다.", "danger")

    return render_template_string(admin_html, admin_pw=pw)

@app.route("/filelist")
def filelist():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({"ok": False, "error": "Unauthorized", "files": []}), 401
    files = [f for f in os.listdir(BOOKS_DIR) if f.endswith(".xlsx")]
    files.sort(reverse=True)
    return jsonify({"ok": True, "files": files})

@app.route("/download/<path:filename>")
def download_file(filename):
    if request.args.get("pw") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    file_path = os.path.join(BOOKS_DIR, filename)
    if os.path.exists(file_path) and filename.endswith(".xlsx"):
        try:
            return send_from_directory(BOOKS_DIR, filename, as_attachment=True, download_name=filename)
        except TypeError:
            return send_from_directory(BOOKS_DIR, filename, as_attachment=True, attachment_filename=filename)
    return "File not found", 404

@app.route("/deletefile/<path:filename>", methods=["POST"])
def delete_file(filename):
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({"success": False, "msg": "권한 없음"}), 401
    file_path = os.path.join(BOOKS_DIR, filename)
    if os.path.exists(file_path) and filename.endswith(".xlsx"):
        os.remove(file_path)
        return jsonify({"success": True})
    return jsonify({"success": False, "msg": "File not found"}), 404

@app.route("/uploaded_img")
def uploaded_img():
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(BOOKS_DIR, IMAGE_BASENAME + ext)
        if os.path.exists(p):
            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            return send_file(p, mimetype=mime)
    return "No image", 404

# ===================== 앱 시작 (waitress) =====================
if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)
