import os
import time
import pandas as pd
from flask import (
    Flask, render_template_string, request, send_file, flash,
    send_from_directory, jsonify, redirect, url_for
)
from werkzeug.utils import secure_filename

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
      /* 화면에 좀 더 크고 꽉 차게 보이도록 상향 */
      --gap: clamp(18px, 3.5vw, 44px);
      --pad: clamp(18px, 3.6vw, 48px);
      --radius: clamp(16px, 3.2vw, 44px);
      --img-h: clamp(320px, 50vh, 600px); /* 이미지 박스 높이 키움 */
      --h1: clamp(1.7rem, 2.8vw, 2.6rem); /* 제목 폰트 크게 */
      --text: clamp(1.02rem, 1.15vw, 1.18rem);
      --btn-fz: clamp(1rem, 1.25vw, 1.2rem);
      --btn-py: clamp(12px, 1.4vw, 18px);
      --btn-px: clamp(22px, 2.4vw, 40px);
      --input-fz: clamp(1.05rem, 1.25vw, 1.25rem);
      --input-pd: clamp(12px, 1.5vw, 18px);
      --max-input: 640px; /* 검색 입력칸 최대 너비 */
    }

    body{
      background:linear-gradient(135deg,#e0f7fa 60%,#f8bbd0 100%);
      font-family:'Noto Sans KR',sans-serif;
      margin:0; min-height:100vh;
    }
    .flex-wrap{
      display:flex; flex-wrap:wrap; justify-content:center; align-items:stretch;
      max-width:1440px; margin:clamp(16px,4.5vh,40px) auto;
      gap:var(--gap);
    }
    .container{
      max-width:740px;          /* 카드 자체도 조금 더 크게 */
      flex:1 1 660px; min-width:340px;
      padding:var(--pad);
      border-radius:var(--radius); background:white;
      box-shadow:0 10px 56px #b2dfdb80; text-align:center;
      border:2px solid #00bfae20; display:flex; flex-direction:column;
    }
    .imgbox{
      flex:1 1 520px; max-width:640px; min-width:320px;
      background:rgba(255,255,255,0.90); border-radius:var(--radius);
      box-shadow:0 10px 56px #b2dfdb30; display:flex; align-items:center; justify-content:center;
      padding:24px 20px; margin:0; min-height:var(--img-h);
    }
    .imgbox img{
      max-width:100%; max-height:calc(var(--img-h) - 16px);
      border-radius:32px; box-shadow:0 2px 18px #b2dfdb40; object-fit:contain;
    }
    h1{ color:#00695c; font-size:var(--h1); font-weight:bold; margin-bottom:18px; letter-spacing:-1px; }

    /* 폼을 중앙 정렬 */
    form{
      margin-bottom:10px;
      display:flex; flex-direction:column; align-items:center; gap:10px;
    }
    /* 입력칸을 정확히 화면/컨테이너의 중앙에 */
    input[type="text"]{
      display:block;
      width:min(var(--max-input), 96%);  /* 너무 넓지 않도록 최대 너비 적용 */
      max-width:var(--max-input);
      margin:0 auto;                     /* 수평 중앙 정렬 */
      font-size:var(--input-fz);
      padding:var(--input-pd);
      border-radius:16px;
      border:1.8px solid #b2dfdb;
      box-sizing:border-box;             /* 패딩/보더 포함해 정확히 가운데 */
      text-align:left;
    }
    button{
      padding:var(--btn-py) var(--btn-px);
      margin:10px; border-radius:18px; background:#00bfae; color:white; border:none;
      cursor:pointer; font-weight:bold; font-size:var(--btn-fz); transition:0.18s;
      box-shadow:0 2px 12px #00bfae20;
      align-self:center;
    }
    button:hover{ background:#00acc1; }
    .result-box{ margin-top:26px;}
    table{
      width:100%; border-collapse:separate; border-spacing:0 10px;
      font-size:var(--text);
    }
    th, td{
      border:1.8px solid #b2dfdb; padding:12px 12px; border-radius:14px; background:white;
    }
    th{ background:#00bfae; color:white; font-weight:700; }
    tr:nth-child(even) td{ background:#f0f5f5; }
    .admin-btns{ margin-top: clamp(36px, 8vh, 120px); }

    @media (max-width: 1280px), (max-height: 820px){
      .flex-wrap{ gap: clamp(14px,2.4vw,26px); margin: clamp(10px,2.6vh,22px) auto; }
      .container{ max-width:700px; flex:1 1 620px; }
      .imgbox{ min-height: clamp(280px, 44vh, 520px); padding:18px; }
      .admin-btns{ margin-top: clamp(28px, 7vh, 90px); }
      th, td{ padding:10px 10px; border-radius:12px; }
    }

    @media (max-width: 900px){
      .flex-wrap{ flex-direction:column; align-items:center; }
      .container, .imgbox{ max-width:96vw; }
    }

    #pwModal{
      display:none; position:fixed; left:0; top:0; width:100vw; height:100vh;
      background:rgba(0,0,0,0.21); z-index:9999; justify-content:center; align-items:center;
    }
    #pwModal .modal-inner{
      background:white; padding:24px 28px 18px 28px; border-radius:18px; min-width:320px;
      box-shadow:0 4px 30px #0001; text-align:center; position:relative
    }
    #pwModal .close-x{ position:absolute; top:7px; right:13px; font-size:1.45em; cursor:pointer; color:#ccc; }
    #pwModal input{ padding:10px 14px; border:1.2px solid #b2dfdb; border-radius:10px; width:80%; box-sizing:border-box; }
    #pwModal .btn{ background:#00bfae; color:white; padding:9px 18px; border-radius:10px; font-weight:bold; border:none; margin-top:12px; cursor:pointer }
    #pwModal .cancel{ background:#eee; color:#888; margin-left:8px; }
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
        <div style="color:#666;font-size:2em;margin-top:24px;">아직 준비되지 않은 도서 입니다</div>
      {% endif %}

      <div class="admin-btns">
        <button onclick="showPwModal();return false;" style="background:#00bfae;">관리자/도서업데이트</button>
      </div>

      <!-- 비번 팝업: 서버로 POST하여 검증 후 관리자 페이지 렌더 -->
      <div id="pwModal">
        <div class="modal-inner">
          <div style="font-size:1.08em;font-weight:bold;margin-bottom:10px;">관리자 비밀번호</div>
          <form id="pwForm" method="post" action="/dodo-manager">
            <input type="password" name="password" placeholder="비밀번호" required>
            <input type="hidden" name="action" value="login">
            <br>
            <button type="submit" class="btn">확인</button>
            <button type="button" class="btn cancel" onclick="hidePwModal()">취소</button>
          </form>
          <span class="close-x" onclick="hidePwModal()">×</span>
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
        <div style="color:#aaa;font-size:1.14em;">(아직 첨부된 이미지가 없습니다)</div>
      {% endif %}
    </div>
  </div>
</body>
</html>
'''

# 관리자 로그인 폼 (GET 접근/실패 시)
admin_login_html = r'''
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>관리자 로그인 | 만화카페 도도</title></head>
<body style="font-family:'Noto Sans KR',sans-serif; background:#f6fcf8;">
  <div style="max-width:480px;margin:80px auto;background:#fff;padding:28px;border-radius:16px;box-shadow:0 8px 24px #00000014;text-align:center">
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
             style="padding:12px;border:1px solid #b2dfdb;border-radius:10px;width:70%">
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

# 관리자 화면 (하단 두 컨트롤 통일 스타일, Blob 다운로드)
admin_html = r'''
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"><title>도서관리 | 만화카페 도도</title>
  <style>
    body{background:#f6fcf8;font-family:'Noto Sans KR',sans-serif;}
    .container{max-width:970px;margin:60px auto;padding:36px 44px 24px 44px;border-radius:44px;background:white;box-shadow:0 8px 32px #b2dfdb60;text-align:center;}
    h1{color:#00bfae;margin-bottom:24px;}
    input,button{padding:13px;margin:10px;border-radius:16px;border:1.5px solid #b2dfdb;}
    button{background:#00bfae;color:white;border:none;cursor:pointer;font-weight:bold;}
    button:hover{background:#00acc1;}
    ul.flash{list-style:none;padding:0;}
    li.success{color:green;} li.danger{color:red;}
    a{color:#00bfae;margin:0 8px;}
    .filelabel{font-size:1.09em;color:#009b7d;margin-top:14px;}
    #downloadModal{display:none;position:fixed;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.21);z-index:9999;justify-content:center;align-items:center;}
    #downloadModal .modal-inner{background:white;padding:32px 32px 20px 32px;border-radius:18px;min-width:320px;box-shadow:0 4px 30px #0001;text-align:center;position:relative;}
    #downloadModal .close-x{position:absolute;top:7px;right:13px;font-size:1.45em;cursor:pointer;color:#ccc;}
    #downloadModal button{background:#00bfae;color:white;padding:7px 20px;border-radius:10px;font-weight:bold;border:none;margin-top:12px;}
    #downloadModal button.cancel{background:#eee;color:#888;margin-left:7px;}
    #downloadModal ul{text-align:left;margin:10px auto;padding:0;max-height:300px;overflow:auto;}
    #downloadModal li{margin:5px 0;list-style:none;display:flex;align-items:center;justify-content:space-between;}
    #downloadModal .filename{max-width:220px;overflow:hidden;text-overflow:ellipsis;}
    #downloadModal .download-btn{background:#00796b;font-size:0.97em;}
    #downloadModal .delete-btn{background:#c62828;color:white;font-size:0.97em;}
    #status{margin-top:8px;color:#c62828;font-size:0.95em;}

    /* 통일 텍스트 버튼 스타일 */
    .linklike{
      background:none;
      border:none;
      color:#00bfae;
      cursor:pointer;
      text-decoration:underline;
      font-weight:600;
      font-size:1rem;
      font-family:inherit;
      padding:0;
    }
    .linklike:hover{
      color:#00acc1;
      text-decoration:none;
    }
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
      <button id="openDownload" type="button" class="linklike">
        기존 도서 데이터 다운로드/삭제
      </button>
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
    // 버튼 클릭 시 모달 열기
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

    function setStatus(msg){
      var s = document.getElementById('status');
      if(s){ s.textContent = msg || ''; }
    }

    function loadFileList(){
      setStatus('');
      fetch('/filelist?pw={{ admin_pw }}')
        .then(function(r){
          if(!r.ok){ setStatus('목록 로드 실패: ' + r.status); }
          return r.json();
        })
        .then(function(data){
          var ul=document.getElementById('fileList');
          if(!data){ ul.innerHTML='<li>오류: 응답 없음</li>'; return; }
          if(data.error){ ul.innerHTML='<li>'+ (data.error || '오류') +'</li>'; return; }
          if(!data.files || data.files.length==0){ ul.innerHTML='<li>파일이 없습니다</li>'; return; }
          ul.innerHTML='';
          data.files.forEach(function(file){
            var li=document.createElement('li');
            var nameSpan = document.createElement('span');
            nameSpan.className='filename';
            nameSpan.textContent = file;

            var dBtn = document.createElement('button');
            dBtn.className='download-btn';
            dBtn.textContent='다운로드';
            dBtn.addEventListener('click', function(){ downloadFile(file); });

            var delBtn = document.createElement('button');
            delBtn.className='delete-btn';
            delBtn.textContent='삭제';
            delBtn.addEventListener('click', function(){ deleteFile(file); });

            li.appendChild(nameSpan);
            li.appendChild(dBtn);
            li.appendChild(delBtn);
            ul.appendChild(li);
          });
        })
        .catch(function(err){
          setStatus('목록 로드 오류: ' + (err && err.message ? err.message : err));
        });
    }

    // Blob 다운로드 방식
    function downloadFile(fname){
      setStatus('');
      const url = '/download/' + encodeURIComponent(fname) + '?pw={{ admin_pw }}';
      fetch(url)
        .then(function(resp){
          if(!resp.ok){ setStatus('다운로드 실패: ' + resp.status); return null; }
          return resp.blob().then(function(blob){
            const a = document.createElement('a');
            const objectUrl = URL.createObjectURL(blob);
            a.href = objectUrl;
            a.download = fname;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(objectUrl);
            a.remove();
          });
        })
        .catch(function(err){
          setStatus('다운로드 오류: ' + (err && err.message ? err.message : err));
        });
    }

    function deleteFile(fname){
      setStatus('');
      if(!confirm(fname+' 파일을 삭제하시겠습니까?')) return;
      fetch('/deletefile/'+encodeURIComponent(fname)+'?pw={{ admin_pw }}', {method:'POST'})
        .then(function(r){
          if(!r.ok){ setStatus('삭제 실패: ' + r.status); return null; }
          return r.json();
        })
        .then(function(data){
          if(!data) return;
          if(data.success){ loadFileList(); }
          else{ setStatus(data.msg || '삭제 실패'); }
        })
        .catch(function(err){
          setStatus('삭제 오류: ' + (err && err.message ? err.message : err));
        });
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

    # ISBN은 숫자로 읽히면 깨질 수 있으므로 문자열로 강제
    df = pd.read_excel(latest_file, dtype={'ISBN': str})

    required = ["제목", "최종권수", "저자", "ISBN", "위치"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"엑셀에 {missing} 컬럼이 없습니다!")

    # NaN/None/'nan'/'null' -> 공백
    df = df.fillna('')
    df = df.applymap(lambda x: '' if (isinstance(x, str) and x.strip().lower() in ('nan', 'none', 'null')) else x)

    # 정수처럼 보이는 값은 소수점 제거 (12.0 -> 12)
    def clean_int_like(x):
        if x == '' or x is None:
            return ''
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
    # 1) 팝업/로그인 폼에서 넘어온 비밀번호 검사
    if request.method == "POST" and request.form.get("action") == "login":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            flash("관리자 인증 성공!", "success")
            # 관리자 화면 렌더 (이후 요청은 hidden field/쿼리로 pw 전달)
            return render_template_string(admin_html, admin_pw=pw)
        else:
            flash("비밀번호가 틀렸습니다.", "danger")
            return render_template_string(admin_login_html)

    # 2) GET 직접 접근 시엔 로그인 폼 표시
    if request.method == "GET":
      return render_template_string(admin_login_html)

    # 3) 관리자 화면 내 액션 처리 (비번 동봉)
    action = request.form.get("action")
    pw = request.form.get("password", "")
    if pw != ADMIN_PASSWORD:
        flash("권한이 없습니다. 다시 로그인해 주세요.", "danger")
        return redirect(url_for("admin"))

    if action == "books":
        file = request.files.get("file")
        if file and allowed_ext(file.filename, ALLOWED_XLSX):
            os.makedirs(BOOKS_DIR, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_name = f"books_{timestamp}.xlsx"
            file.save(os.path.join(BOOKS_DIR, secure_filename(save_name)))
            flash("도서 데이터가 성공적으로 업로드되었습니다!", "success")
        else:
            flash("올바른 엑셀 파일(.xlsx)만 업로드 가능합니다.", "danger")

    elif action == "image":
        imgfile = request.files.get("imgfile")
        if imgfile and allowed_ext(imgfile.filename, ALLOWED_IMG):
            # 기존 이미지 정리(확장자 상관없이 1장만 유지)
            for e in [".jpg", ".jpeg", ".png"]:
                old = os.path.join(BOOKS_DIR, IMAGE_BASENAME + e)
                if os.path.exists(old):
                    try: os.remove(old)
                    except: pass
            ext = os.path.splitext(imgfile.filename)[1].lower()
            save_path = os.path.join(BOOKS_DIR, IMAGE_BASENAME + ext)
            imgfile.save(save_path)
            flash("이미지가 성공적으로 업로드되었습니다!", "success")
        else:
            flash("올바른 이미지 파일(jpg/png)만 업로드 가능합니다.", "danger")

    # 처리 후에도 관리자 화면 유지 (비번 유지 전달)
    return render_template_string(admin_html, admin_pw=pw)

@app.route("/filelist")
def filelist():
    # 쿼리스트링 pw 로 검증
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
            # 최신 Flask/Werkzeug
            return send_from_directory(BOOKS_DIR, filename, as_attachment=True, download_name=filename)
        except TypeError:
            # 구버전 호환
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
    # 공개 이미지
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(BOOKS_DIR, IMAGE_BASENAME + ext)
        if os.path.exists(p):
            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            return send_file(p, mimetype=mime)
    return "No image", 404

# ===================== 앱 시작 (waitress) =====================
if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 5000))  # Render가 PORT를 주입
    serve(app, host="0.0.0.0", port=port)
