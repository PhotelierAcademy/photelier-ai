import os
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Supabaseクライアント
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# 知識ベースを起動時に読み込む
KNOWLEDGE_PATH = Path("knowledge/knowledge_base.txt")
STUDENTS_PATH = Path("students.json")

MONTHLY_LIMIT = 100

knowledge_base = ""
if KNOWLEDGE_PATH.exists():
    knowledge_base = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    print(f"✅ 知識ベース読み込み完了: {len(knowledge_base):,}文字")

SYSTEM_PROMPT = """あなたはPhotelier Academyを運営する「さちえ先生（尾形幸枝）」の分身AIアシスタントです。

## あなたの役割
- テーブルフォトマスターコース（4ヶ月）およびテーブルフォト＋SNS集客コース（6ヶ月）の受講生をサポートする
- 受講生が課題で詰まったとき、24時間いつでも気軽に相談できる存在
- さちえ先生のやり方・言葉遣い・価値観を大切にして答える

## さちえ先生のスタイル
- 温かく親しみやすい口調（「〜だよ」「〜だね」「〜してみてね」）
- 受講生の気持ちに寄り添い、まず共感してからアドバイス
- 具体的で実践しやすいアドバイスを心がける
- できていることを認めてから、改善点を伝える
- 難しく考えすぎず、シンプルに行動できるよう背中を押す
- 絵文字を適度に使って親しみやすく（😊✨📸など）

## 対応できること
1. **テーブルフォト**（ライティング・撮影基礎・レタッチ・世界観設計など）
2. **SNS集客**（ペルソナ設定・コンセプト設計・インスタプロフィール・リール・発信ネタなど）
3. **課題の添削・アドバイス**（具体的な改善提案）
4. **進め方のアドバイス**（どの課題から取り組むべきかなど）
5. **マインド面のサポート**（行き詰まったとき、自信がないときなど）

## 大切にすること
- 受講生が「また相談したい」と思えるような温かい対応
- 課題の答えを教えすぎず、自分で考えて気づけるよう導く
- 「完璧にできてから」ではなく「まず行動」を促す
- 各受講生の進捗や状況に合わせた個別対応

## 注意事項
- 講座の内容に関係ない質問（他のビジネス相談、個人情報など）は丁重にお断りする
- わからないことは「さちえ先生に直接聞いてみてね」と案内する
- 会話の最後には次のアクションを1つ具体的に提案する

---

## SNS集客コース カリキュラム（月別）

【1ヶ月目】
- 世界観イメージマップ作成（Canvaテンプレートあり）
- 現状分析（シートに記入して提出）
- マーケティング全体像の把握（動画を見る）
- ブランディングとマーケティングの違い（動画を見る）
- 売れる市場（動画を見る）
- ペルソナ設定（動画を見て提出）
- 発信の本質（動画を見て発信をはじめる）
- フォロワーの増やし方（動画を見て発信をはじめる）

【2ヶ月目】
- 悩み出し（心配なこと・不安・不満・悩み・解決したいこと・満たしたい欲を100個書き出して提出）
- 解決策（悩み出しから解決できることを列挙して提出）
- リサーチ・モデリング（動画を見てシート提出）
- コンセプト設計（動画を見てシート提出）
- インスタプロフィール（動画を見て提出）
- インスタアイコン（整える）
- 発信ネタ出し・7つの型（動画を見て実践）
- 5つの発信テンプレート（動画を見て実践）
- ストーリーズ投稿（動画を見て実践）
- LINE公式開設（実践）
- インスタにリンクを設定（実践）
- CTAを整える（実践）

【3ヶ月目】
- 講座タイトル（考えて提出）
- BEカリキュラム（シート提出）
- FE（動画を見て実践）
- FEカリキュラム（考えて提出）
- ハイライト（動画を見て実践）
- リール作成（動画を見て実践）
- リール撮影の仕方（動画を見て実践）
- インスタライブ（実践）
- LINEプレゼント作成（AIに相談しながら作成）
- LINE教育配信（実践）

【4ヶ月目】
- 提案書作成（Canvaテンプレートあり）
- FE LP作成（実践）
- 満席を作るLINE告知文（動画を見て実践）

【5ヶ月目】
- クロージング（動画を見て実践）
- マインド（動画を見る）

【6ヶ月目】
- ミッション・ビジョン（シートを見て実践・提出）
- グランドルール設定（シートを見て実践・提出）

「📝 提出」マークのついた課題は、受講生がチャットに内容を書いてAIがフィードバックすること。
フィードバック後は「よければ課題リストにチェックを入れてね！」と促すこと。

## 悩み出しの進め方
受講生が「悩み出し」に取り組む場合：
- 以下の6カテゴリーで合計100個書き出すよう伝える
  ①心配なこと　②不安に思っていること　③不満に思っていること
  ④悩んでいること　⑤解決したいこと　⑥満たしたい欲
- 「完璧じゃなくていい、思いついたことを全部出し切ることが大事！」と背中を押す
- 詰まっていたら「今一番モヤモヤしていることは何？」など質問して引き出す
- 100個書き出したら提出してもらい、「これだけのお客様の悩みに応えられる可能性がある！」と価値を伝えてフィードバックする
- 特に多く出てきたカテゴリーや、コンセプト設計につながりそうな悩みをピックアップしてあげる
- フィードバック後は「よければ課題リストにチェックを入れてね！」と促す

## BEカリキュラムの進め方
受講生が「BEカリキュラム」に取り組む場合、まず現在の状況を確認する：

【FEだけ進めたい段階の場合】
「今はまずFEを回してお客様との関係を作るのが大事だよ！BEはその後でも全然OK😊」と伝え、無理にBE設計を進めない。FEの準備状況を確認してそちらをサポートする。

【BE設計に進む場合】
自分が将来販売する本講座（バックエンド商品）のカリキュラムを一緒に設計する：

まず以下を確認する：
1. 「B地点」＝受講生がこの講座を終えたときにどんな状態になっているか（目標・ゴール）
2. 講座期間（人によって3ヶ月・6ヶ月・それ以外など様々）
3. 何回の講義で構成するか（回数は人によって異なる）
4. 金額の目安
5. サポート内容（個別セッション・グループなど）と実施方法（Zoom・対面など）

次に各回の講義を一緒に組み立てる：
- 各回に「講義タイトル・内容・具体的にやること」を設計する
- 最終回を終えたときにB地点に到達できるよう逆算して考える
- 「最初の回は何を教えたら受講生が前に進めそう？」など質問しながら引き出す
- 全部決まったら内容をまとめてフィードバックし「よければチェックリストにチェックを入れてね！」と促す

## 個別セッションの予約タイミング
個別セッションの予約URLはこちら：https://sub.photelier-academy.com/event/fLms6F9jtGPz/register

【6ヶ月コース：3回】
- 1回目：ペルソナ設定・悩み出し・コンセプト設計が完了したとき
- 2回目：BEカリキュラム・FEカリキュラムが完了したとき
- 3回目：FE LP・提案書が完了したとき（クロージング前）

【8ヶ月コース：6回】
- 1回目：世界観・現状分析・ペルソナ設定が完了したとき
- 2回目：悩み出し・コンセプト設計・インスタ整備が完了したとき
- 3回目：BEカリキュラム・FEカリキュラムが完了したとき
- 4回目：提案書・FE LPが完了したとき
- 5回目：クロージング動画を見たとき
- 6回目：ミッション・ビジョン・グランドルールが完了したとき

受講生が上記の課題完了を報告したら「次は個別セッションを予約するタイミングだよ！」と伝え、予約URLを案内する。予約は3週間先まで取れる。

## ミッション・ビジョンの進め方
受講生が「ミッション・ビジョン」に取り組む場合、会話で一緒に言語化する：

**ミッション（使命）を作る**
1. 「なぜこのビジネスをやろうと思ったの？」と聞く
2. 「どんな価値を届けたい？誰のために？」と深掘りする
3. 出てきた言葉をもとに「〜な人のために、〜を通じて〜を届ける」の形で一緒に整える

**ビジョン（未来像）を作る**
1. 「あなたのミッションが叶った世界はどんな姿？」と聞く
2. 「10年後、あなたのお客様はどう変わっている？社会はどう変わっている？」と広げる
3. 具体的な未来の姿として言語化して整える

さちえ先生のミッション例：「"わたし自身"として人生を自由に選べる女性を増やす」
さちえ先生のビジョン例：「好きな世界観で選ばれ、家族も仕事も大切にしながら自分の人生をデザインできる女性が日本中に広がる未来」を参考に、受講生自身の言葉で作れるよう導く。
完成したらチャットに提出してもらいフィードバックし「よければチェックリストにチェックを入れてね！」と促す。

## グランドルール設定の進め方
受講生が「グランドルール」に取り組む場合、自分のビジネス・コミュニティのルールを一緒に考える：

1. 「あなたの講座やコミュニティで大切にしたいことは何？」と聞く
2. 「受講生にどんな姿勢で取り組んでほしい？」と引き出す
3. 3〜5個のシンプルなルールとして言葉にする

さちえ先生のグランドルール例（Rule1〜5）を参考に伝えてもいい。
完成したらチャットに提出してもらいフィードバックし「よければチェックリストにチェックを入れてね！」と促す。

## インスタライブのサポート方針
- フォロワー1000人以上の受講生にはインスタライブに挑戦するよう積極的に背中を押す
- フォロワー1000人未満の場合は「まずフォロワーを増やしながら準備しておこう！」と伝え、今できる発信（リール・ストーリーズなど）に集中させる
- 「誰も来なかったらどうしよう」「恥ずかしい」などの不安には、資料の内容をもとに共感しながら解消する
- 自己開示ワーク・自己紹介ワークを活用して、ライブで話す内容を一緒に考えてあげる
- 「売らなくていい、まず想いを話すだけでOK」と伝えてハードルを下げる

## 現状分析の進め方
受講生が「現状分析」に取り組む場合、以下の流れで会話形式で進めること：

【売上実績がある場合】
以下を1つずつ聞いて、最後に分析・アドバイスをする：
1. 過去3ヶ月の月間LINE登録者数（見込客数）
2. 個別相談または体験に来た人数
3. その中で成約した人数
4. 売った商品の価格
5. その人が何度購入したか（平均）
→ 入力が揃ったら「売上 = 見込客 × 成約率 × 商品単価 × リピート率」の公式で現状を整理し、一番改善すべきポイントを具体的にアドバイスする。

【売上実績がない・ほぼゼロの場合】
「ゼロからのスタートは、逆に伸びしろしかないってこと！」と前向きに受け止め、分析ではなく目標設定に切り替える：
1. 将来どんな人をサポートしたいか（ターゲット）
2. どんな商品・サービスを売りたいか
3. 6ヶ月後の目標売上（例：月10万円など）
4. 今できることは何か（インスタのフォロワー数、LINE登録者数など）
→ 現状のリソースを把握した上で、まずどこから始めるべきかを具体的に提案する。

---

以下がPhotelier Academyの講座資料・動画文字起こしです。この知識をもとに受講生をサポートしてください：

"""

# ---- Supabaseを使ったデータ管理 ----

def get_member(email: str) -> Optional[dict]:
    """会員（サブスク／これからの本講座受講生）。キーはメールアドレス。"""
    if "@" not in email:
        return None
    try:
        result = supabase.table("members").select("*").eq("email", email.strip().lower()).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ 会員取得エラー: {e}")
        return None


def unlocked_month(member: dict) -> int:
    """入会日から31日ごとに1ヶ月分ずつ開放。0＝入会直後の分だけ。"""
    if member.get("full_unlock") or member.get("tier") == "course":
        return 999
    started = member.get("subscription_started_at")
    if not started:
        return 0
    days = (datetime.now().date() - date.fromisoformat(started)).days
    return max(0, days // 31)


def get_student_info(student_name: str) -> Optional[dict]:
    if STUDENTS_PATH.exists():
        data = json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))
        for s in data["students"]:
            if isinstance(s, dict) and s["name"] == student_name:
                return s
    member = get_member(student_name)
    if member:
        return {
            "name": member["name"],
            "end_date": member.get("support_end"),
            "course_months": member.get("course_months") or 10,
        }
    return None

def get_monthly_count(student_name: str) -> int:
    this_month = datetime.now().strftime("%Y-%m")
    try:
        result = supabase.table("message_counts").select("count").eq("student_name", student_name).eq("month_key", this_month).execute()
        if result.data:
            return result.data[0]["count"]
    except Exception as e:
        print(f"❌ カウント取得エラー: {e}")
    return 0

def increment_monthly_count(student_name: str):
    this_month = datetime.now().strftime("%Y-%m")
    current = get_monthly_count(student_name)
    try:
        supabase.table("message_counts").upsert({
            "student_name": student_name,
            "month_key": this_month,
            "count": current + 1
        }).execute()
    except Exception as e:
        print(f"❌ カウント更新エラー: {e}")

def load_conversation(student_name: str) -> list:
    try:
        result = supabase.table("conversations").select("messages").eq("student_name", student_name).execute()
        if result.data:
            return result.data[0]["messages"]
    except Exception as e:
        print(f"❌ 会話読み込みエラー: {e}")
    return []

def save_conversation(student_name: str, messages: list):
    try:
        supabase.table("conversations").upsert({
            "student_name": student_name,
            "messages": messages,
            "updated_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"❌ 会話保存エラー: {e}")

# ---- APIエンドポイント ----

class ChatRequest(BaseModel):
    student_name: str
    message: str
    image: Optional[str] = None
    image_type: Optional[str] = None

class ResetRequest(BaseModel):
    student_name: str

# 入口は3つ。中身は同じ1枚で、開いたアドレスによって最初の画面だけ変える。
#   /        … サロン会員（8/28のLPからここへ来る）
#   /course  … 本講座の受講生（入り方は会員さんと同じ。見出しだけ変わる）
#   /old     … これまでの6名（お名前＋合言葉）。11月にこの入口ごと消せる。

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/course")
async def course_login():
    return FileResponse("static/index.html")


@app.get("/old")
async def legacy_login():
    return FileResponse("static/index.html")

@app.get("/api/students")
async def get_students(authorization: str = Header(None)):
    # 受講生のお名前は、合言葉が合っている方にだけお見せする。
    # 誰にでも見えると「誰が受講しているか」が外から分かってしまう。
    if legacy_pass_from_auth(authorization) != LEGACY_PASSCODE or not LEGACY_PASSCODE:
        raise HTTPException(status_code=401, detail="合言葉が必要です")
    if STUDENTS_PATH.exists():
        data = json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))
        students = data.get("students", [])
        names = [s["name"] if isinstance(s, dict) else s for s in students]
        names.sort(key=lambda n: 1 if "テスト" in n else 0)
        return {"students": names}
    return {"students": []}

# ---- 会員ログイン（サブスク／これからの本講座受講生）----
# 既存6名は students.json のまま「名前を選ぶだけ」で入れる。ここは新しい会員だけが通る道。
# パスワードは Supabase Auth が預かる（このアプリは受け取らないし保存もしない）。

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


def member_public(member: dict) -> dict:
    return {
        "key": member["email"],
        "name": member["name"],
        "tier": member["tier"],
        "unlocked_month": unlocked_month(member),
        "full_unlock": member.get("full_unlock", False),
        "subscription_started_at": member.get("subscription_started_at"),
        "support_end": member.get("support_end"),
        "alumni": member.get("alumni", False),
        "continuing": member.get("continuing", False),
    }


@app.post("/api/login")
async def login(request: LoginRequest):
    email = request.email.strip().lower()
    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
            json={"email": email, "password": request.password},
        )
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="メールアドレスかパスワードが違うみたいです")

    member = get_member(email)
    if not member:
        raise HTTPException(status_code=403, detail="会員情報が見つかりませんでした。さちえ先生にご連絡ください")
    if not member.get("active", True):
        raise HTTPException(status_code=403, detail="サロンのご利用期間が終了しています。またいつでもお戻りくださいね😊")

    data = res.json()
    return {
        "token": data["access_token"],
        # 札（トークン）は1時間で切れる。切れたときに入り直していただかなくて済むよう、
        # 取り直すための控え（refresh_token）も一緒にお渡しする。
        "refresh": data.get("refresh_token"),
        "member": member_public(member),
    }


@app.post("/api/refresh")
async def refresh_token(body: RefreshRequest):
    """期限が切れた札を、控えを使って取り直す。（控えも毎回新しくなる）"""
    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
            json={"refresh_token": body.refresh_token},
        )
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="ログインし直してください")
    data = res.json()
    return {"token": data["access_token"], "refresh": data.get("refresh_token")}


async def member_from_token(authorization: Optional[str]) -> dict:
    """ログイン中の会員を、預かっているトークンから取り出す。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_KEY, "Authorization": authorization},
        )
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="ログインの有効期限が切れました")

    member = get_member(res.json().get("email", ""))
    if not member:
        raise HTTPException(status_code=403, detail="会員情報が見つかりませんでした")
    # 退会された方。責める言い方にならないように。
    if not member.get("active", True):
        raise HTTPException(status_code=403, detail="サロンのご利用期間が終了しています。またいつでもお戻りくださいね😊")
    return member


@app.get("/api/me")
async def me(authorization: str = Header(None)):
    """保存しておいたトークンで、ログイン状態を復元する。"""
    return {"member": member_public(await member_from_token(authorization))}


# ---- そのデータが、その人のものかを確かめる ----
# 会員（メールアドレスでログインする方）のデータは、本人のトークンがないと触れない。
# 既存6名（お名前を選んで入る方）は、11月にサポートが終わるまで今のまま。

TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD")


def is_teacher(teacher_key: Optional[str]) -> bool:
    return bool(TEACHER_PASSWORD) and teacher_key == TEACHER_PASSWORD


def require_teacher(teacher_key: Optional[str]):
    if not is_teacher(teacher_key):
        raise HTTPException(status_code=401, detail="先生用のパスワードが必要です")


# 既存6名（お名前を選んで入る方）の合言葉。
# これが無いと「名前を選ぶだけ」で誰にでもなれてしまい、
# その方の相談履歴も、動画102本も、外から読めてしまう。
# 8/28にサイトを公開したら、URL を知っている人＝世界中になるので必ず要る。
# 11月に全員がメールアドレスのログインへ移ったら、この仕組みごと消してよい。
LEGACY_PASSCODE = os.getenv("LEGACY_PASSCODE")


def legacy_pass_from_auth(authorization: Optional[str]) -> Optional[str]:
    """既存6名は「Legacy 合言葉」の形で送ってくる。
    会員は「Bearer トークン」なので、同じ入口を相乗りで使える。
    こうすると、ひとつひとつの窓口を書き換えずに済む。"""
    if authorization and authorization.startswith("Legacy "):
        return authorization[len("Legacy "):].strip()
    return None


def is_legacy_ok(student_name: Optional[str], legacy_pass: Optional[str]) -> bool:
    """お名前が既存6名にあり、かつ合言葉が合っているときだけ True。"""
    if not LEGACY_PASSCODE or not legacy_pass:
        return False
    if not student_name or student_name not in legacy_names():
        return False
    return legacy_pass == LEGACY_PASSCODE


async def require_owner(student_name: str, authorization: Optional[str],
                        teacher_key: Optional[str] = None):
    """会員のデータは、本人とさちえ先生だけが触れる。"""
    if is_teacher(teacher_key):
        return
    if "@" not in (student_name or ""):
        # 既存6名。合言葉が合っていなければ通さない。
        if is_legacy_ok(student_name, legacy_pass_from_auth(authorization)):
            return
        raise HTTPException(status_code=401, detail="合言葉が必要です")
    member = await member_from_token(authorization)
    if member["email"].strip().lower() != student_name.strip().lower():
        raise HTTPException(status_code=403, detail="ほかの方のデータは見られません")


# ---- 動画教材の一覧 ----
# このファイルは static に置かない。static に置くと、ログインしていない人でも
# URL を開くだけで全102本の Vimeo ID と限定公開ハッシュが読めてしまい、
# サブスクも全開放（49,800円）も意味がなくなるため。
# ここでは「その人が今日見ていい分」だけを渡す。まだ開いていない回は
# タイトルは残して ID を外す（何ヶ月目に開くかは画面に出したいので）。

LIBRARY_PATH = Path("data/video_library.json")


# ---- AIさちえ先生に「どの動画があるか」を覚えていただく ----
# これを渡しておかないと、「どの動画から見たらいい？」と聞かれたときに
# 実在しない動画名を作ってしまう。カテゴリと本当のタイトルだけを渡す。

def build_video_catalog() -> str:
    try:
        data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ 動画一覧を読めませんでした: {e}")
        return ""
    lines = []
    for c in data.get("categories", []):
        # リアルセミナーは40本あり、日付ごとの記録なので「見る順番」の案内には使わない
        if c.get("slug") == "seminar":
            continue
        titles = [v.get("title") for v in c.get("videos", []) if v.get("title")]
        if not titles:
            continue
        lines.append(f"\n【{c.get('ja')}】")
        lines += [f"- {t}" for t in titles]
    return "\n".join(lines)


VIDEO_GUIDE = """

---

## 動画教材の一覧（ご案内していいのは、この中にあるものだけ）
""" + build_video_catalog() + """

## 「どの動画から見たらいいですか？」と聞かれたときの答え方

必ずこの順で進めること。

1. まず2つだけおたずねする（3つ以上は聞かない）
   ・いま何を撮りたいか（ご自分の作品／販売する商品／お教室の様子 など）
   ・いちばんの悩みはどれに近いか（撮り方が分からない／写真がそろわない／撮れるけれど集客につながらない）
2. 上の一覧から **3本だけ** 選び、見る順番に並べてお伝えする。4本以上は出さない
3. 1本ごとに「なぜこの方にこれが要るのか」を1行そえる
4. 最後に「まず1本目を見て、撮った1枚を持ってきてくださいね」と結ぶ

選び方の目安
- 撮り方そのものが不安 → スマホ・カメラ基礎 → テーブルフォト
- 写真の雰囲気がそろわない・自分の色が分からない → 世界観設計 → テーブルフォト
- きれいに撮れるのに暗い・色が濁る → ライティング → レタッチ
- 撮れるけれど集客につながらない → 世界観設計 → マーケティング基礎 → インスタ発信・集客
- 発信しているのに申し込みが来ない → インスタ発信・集客 → 商品設計・LP・セールス

★一覧にない動画の名前を作らないこと。近いものが分からなければ、一覧の中から選び直す。
★1本目を見終えた方が戻ってきたら、次の1本と、その前に撮ってみることを1つだけお伝えする。
"""


def legacy_names() -> list:
    """お名前を選んで入る方（既存6名）。11月にサポートが終わるまでの経過措置。"""
    if not STUDENTS_PATH.exists():
        return []
    data = json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))
    return [s["name"] if isinstance(s, dict) else s for s in data.get("students", [])]


def video_is_open(v: dict, c: dict, tier: str, unlocked: int) -> bool:
    """index.html の isVideoOpen と同じ判定。ここが本物で、画面側は見た目のため。"""
    if tier == "course":
        return True
    if isinstance(v.get("m"), int):
        return v["m"] <= unlocked
    if c.get("course_only"):
        return False
    return (c.get("month") or 0) <= unlocked


def hides_seminar(member: dict) -> bool:
    """水曜のリアルセミナーを画面から隠す方か。
    隠すのは卒業生だけ（2026-10-30 本人指示）。
    ★ 継続コースの方は卒業生サロンにも参加できる＝alumni を立てるが、
      水曜にも出ていらっしゃるので隠さない（2026-11-04 本人指示）。"""
    return bool(member.get("alumni")) and not bool(member.get("continuing"))


async def viewer_scope(authorization: Optional[str], x_teacher_key: Optional[str],
                       student_name: Optional[str]) -> tuple:
    """動画を見ていい人かを確かめて、(tier, 開放月, 水曜セミナーを隠すか) を返す。
    さちえ先生 → 全部 / 会員 → トークンで判定 / 既存6名 → お名前＋合言葉で。
    どれでもなければ 401。"""
    if is_teacher(x_teacher_key):
        return "course", 999, False
    legacy_pass = legacy_pass_from_auth(authorization)
    if legacy_pass is not None:
        if is_legacy_ok(student_name, legacy_pass):
            return "course", 999, False
        raise HTTPException(status_code=401, detail="合言葉が必要です")
    if authorization:
        member = await member_from_token(authorization)
        return member["tier"], unlocked_month(member), hides_seminar(member)
    raise HTTPException(status_code=401, detail="ログインが必要です")


@app.get("/api/library")
async def library(authorization: str = Header(None),
                  x_teacher_key: str = Header(None),
                  student_name: str = None):
    tier, unlocked, hide_seminar = await viewer_scope(authorization, x_teacher_key, student_name)
    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    # リアルセミナー（毎週水曜）は受講中の方の場。卒業生には出さない（2026-10-30 本人指示）。
    # 卒業生サロンのアーカイブが代わりにある。継続コースの方には出す。
    if hide_seminar:
        data["categories"] = [c for c in data.get("categories", [])
                              if c.get("slug") != "seminar"]
    for c in data.get("categories", []):
        for v in c.get("videos", []):
            # リアルセミナーは、本講座の方には完全版、それ以外にはカット版を見ていただく。
            # （良かったことシェアは受講生の個人的なお話なので、サロンには出さない）
            # 入れ替えはここサーバー側でやる。cut は必ず消すので、
            # サロンの方のブラウザに完全版の動画IDが届くことは一度もない。
            cut = v.pop("cut", None)
            if cut and tier != "course":
                v["id"] = cut.get("id")
                if cut.get("h"):
                    v["h"] = cut["h"]
                else:
                    v.pop("h", None)
                # 要約は完全版のことを書いてあって、良かったことシェア（お名前入り）も
                # 混ざっている。カット版には付けない。
                v.pop("summary", None)
                if cut.get("summary"):
                    v["summary"] = cut["summary"]
            if not video_is_open(v, c, tier, unlocked):
                v["id"] = None
                v.pop("h", None)
                # まだ開いていない動画の要約も送らない
                v.pop("summary", None)
    return data


# ---- サブスク申し込み（Stripe）----
# 流れ: LP の申込ボタン → /subscribe → Stripe Checkout → /welcome?session_id=...
#       → その場でパスワードを決めてもらう → /api/signup-complete で会員発行 → そのままログイン
# 会員登録メールは送らない（Supabase の無料枠は送信数が少なく、募集で詰まるため）。

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
# 商品IDとクーポンIDは、テストと本番で別物になる。
# ここに初期値を書いてしまうと、本番なのにテストの商品で決済されてしまうので、
# 必ず環境変数（ローカルは .env、公開後は Render の Environment）から読む。
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_FIRST_MONTH_COUPON = os.getenv("STRIPE_FIRST_MONTH_COUPON")
STRIPE_API = "https://api.stripe.com/v1"


async def stripe_call(method: str, path: str, data: Optional[dict] = None,
                      idempotency_key: Optional[str] = None) -> dict:
    # data は必ず dict で渡す。httpx はリストを「生データ」と解釈してしまい送信に失敗する。
    # idempotency_key を渡すと、二重送信されても課金は1回だけになる。
    url = f"{STRIPE_API}{path}"
    auth = (STRIPE_SECRET_KEY, "")
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
    async with httpx.AsyncClient(timeout=20) as http:
        if method == "POST":
            res = await http.post(url, auth=auth, data=data, headers=headers)
        else:
            res = await http.get(url, auth=auth)
    body = res.json()
    if res.status_code >= 400:
        print(f"❌ Stripeエラー: {body}")
        raise HTTPException(status_code=502, detail="決済システムに接続できませんでした")
    return body


@app.get("/salon")
async def salon_lp():
    """サブスク（Photelier サロン）の申込ページ。"""
    return FileResponse("static/salon-lp.html")


@app.get("/subscribe")
async def subscribe(request: Request):
    """LP の申込ボタンの飛び先。Stripe の決済画面へ送る。"""
    if not (STRIPE_PRICE_ID and STRIPE_FIRST_MONTH_COUPON):
        raise HTTPException(500, "決済の設定が読み込めていません（STRIPE_PRICE_ID / STRIPE_FIRST_MONTH_COUPON）")
    base = str(request.base_url).rstrip("/")
    session = await stripe_call("POST", "/checkout/sessions", {
        "mode": "subscription",
        "line_items[0][price]": STRIPE_PRICE_ID,
        "line_items[0][quantity]": "1",
        "discounts[0][coupon]": STRIPE_FIRST_MONTH_COUPON,
        "success_url": f"{base}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/",
        "locale": "ja",
        "billing_address_collection": "auto",
    })
    return RedirectResponse(session["url"], status_code=303)


@app.get("/welcome")
async def welcome_page():
    return FileResponse("static/welcome.html")


@app.get("/api/checkout/{session_id}")
async def checkout_status(session_id: str):
    """決済が完了しているか、どのメールアドレスで払われたかを返す。"""
    session = await stripe_call("GET", f"/checkout/sessions/{session_id}")
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="お支払いがまだ完了していないようです")
    email = (session.get("customer_details") or {}).get("email", "").strip().lower()
    return {
        "email": email,
        "name": (session.get("customer_details") or {}).get("name") or "",
        "already_registered": get_member(email) is not None,
    }


class SignupCompleteRequest(BaseModel):
    session_id: str
    name: str
    password: str


@app.post("/api/signup-complete")
async def signup_complete(request: SignupCompleteRequest):
    """決済直後にパスワードを決めてもらい、会員を発行してそのままログインさせる。"""
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="パスワードは8文字以上にしてください")
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="お名前を入れてください")

    session = await stripe_call("GET", f"/checkout/sessions/{request.session_id}")
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="お支払いが確認できませんでした")
    email = (session.get("customer_details") or {}).get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="メールアドレスが取得できませんでした")
    if get_member(email):
        raise HTTPException(status_code=409, detail="このメールアドレスはすでに登録済みです。ログイン画面からお入りください")

    async with httpx.AsyncClient(timeout=20) as http:
        created = await http.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json"},
            json={"email": email, "password": request.password, "email_confirm": True},
        )
    if created.status_code >= 400:
        # ここで一番怖いのは「お支払いは済んでいるのに入れない」状態。
        # メールアドレスがすでに使われている場合は、ログイン画面へ案内する
        # （パスワードを忘れていても、ログイン画面から再設定できる）。
        print(f"❌ 会員作成エラー ({email}): {created.text}")
        if "already" in created.text.lower() or created.status_code == 422:
            raise HTTPException(status_code=409,
                                detail="このメールアドレスはすでにお使いです。ログイン画面からお入りください。"
                                       "パスワードがご不明なときは、ログイン画面の「パスワードを忘れた方」からお進みください")
        raise HTTPException(status_code=500, detail="登録に失敗しました。さちえ先生にご連絡ください")

    try:
        supabase.table("members").insert({
            "id": created.json()["id"],
            "email": email,
            "name": name,
            "tier": "subscription",
            "subscription_started_at": datetime.now().date().isoformat(),
            "stripe_customer_id": session.get("customer"),
            "stripe_subscription_id": session.get("subscription"),
        }).execute()
    except Exception as e:
        # お支払いは通っている。ログの内容をそのまま伝えれば手で直せる。
        print(f"❌ 会員の行が作れませんでした ({email} / stripe={session.get('customer')}): {e}")
        raise HTTPException(status_code=500,
                            detail="お支払いは完了していますが、登録の最後で止まりました。"
                                   "お手数ですがさちえ先生にご連絡ください（二重にお支払いは発生しません）")

    return await login(LoginRequest(email=email, password=request.password))


# ---- 本講座の受講生を、さちえ先生が1人ずつ発行する ----
# サロンはカード決済のときに自動で会員ができる。
# 本講座はリアルでお申し込みいただくので、先生の画面から手で作る。
# 作った方は最初から全部の動画が見られる（tier = course）。
# 最初のパスワードは先生が決めてお伝えし、ご本人があとから変えられる。

class NewCourseMember(BaseModel):
    email: str
    name: str
    password: str
    support_end: Optional[str] = None   # サポートの終わる日（空でもよい）
    alumni: Optional[bool] = False      # 卒業生サロンの方は true（アーカイブが全部見られる）
    continuing: Optional[bool] = False  # 継続コースの方は true（alumni と両方立てる。水曜も出る）


@app.get("/api/members")
async def list_members(x_teacher_key: str = Header(None)):
    """会員さんの一覧。ここで退会の切り替えもする。"""
    require_teacher(x_teacher_key)
    cols = "id,email,name,tier,active,full_unlock,support_end,subscription_started_at,created_at"
    # openchat_name / alumni / continuing は、それぞれの schema SQL をまだ実行していないと列が無い。
    # どの段階でも先生ページを止めないよう、無い列を落としながら読む。
    for extra in (",openchat_name,alumni,continuing", ",openchat_name,alumni",
                  ",openchat_name", ",alumni", ""):
        try:
            rows = supabase.table("members").select(
                cols + extra).order("created_at", desc=True).execute().data or []
            break
        except Exception:
            continue
    return {"members": rows}


@app.post("/api/members")
async def create_course_member(request: NewCourseMember, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    email = request.email.strip().lower()
    name = request.name.strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="メールアドレスの形になっていないようです")
    if not name:
        raise HTTPException(status_code=400, detail="お名前を入れてください")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="最初のパスワードは8文字以上にしてください")
    if get_member(email):
        raise HTTPException(status_code=409, detail="このメールアドレスはすでに登録されています")

    async with httpx.AsyncClient(timeout=20) as http:
        created = await http.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json"},
            json={"email": email, "password": request.password, "email_confirm": True},
        )
    if created.status_code >= 400:
        print(f"❌ 受講生の作成エラー ({email}): {created.text}")
        if "already" in created.text.lower() or created.status_code == 422:
            raise HTTPException(status_code=409, detail="このメールアドレスはすでにお使いです")
        raise HTTPException(status_code=500, detail="作成できませんでした")

    row = {
        "id": created.json()["id"],
        "email": email,
        "name": name,
        "tier": "course",
        "support_end": request.support_end or None,
        # 継続コースの方は卒業生サロンにも参加できるので、alumni も一緒に立てる
        "alumni": bool(request.alumni) or bool(request.continuing),
        "continuing": bool(request.continuing),
    }
    try:
        supabase.table("members").insert(row).execute()
    except Exception:
        # continuing 列をまだ作っていないとき（schema_alumni.sql 未実行）でも作れるように
        row.pop("continuing", None)
        try:
            supabase.table("members").insert(row).execute()
        except Exception as e:
            print(f"❌ 受講生の行が作れませんでした ({email}): {e}")
            raise HTTPException(status_code=500, detail="最後のところで止まりました。もう一度お試しください")

    return {"ok": True, "email": email, "name": name}


class MemberActive(BaseModel):
    active: Optional[bool] = None
    alumni: Optional[bool] = None       # 卒業生サロンの方か
    continuing: Optional[bool] = None   # 継続コースの方か（水曜も出る）


@app.patch("/api/members/{member_id}")
async def update_member(member_id: str, request: MemberActive, x_teacher_key: str = Header(None)):
    """在籍中↔退会 の切り替えと、種別（本講座／卒業生／継続コース）の変更。
    退会にすると、その場で入れなくなる。"""
    require_teacher(x_teacher_key)
    patch = {}
    if request.active is not None:
        patch["active"] = request.active
    if request.alumni is not None:
        patch["alumni"] = request.alumni
    if request.continuing is not None:
        patch["continuing"] = request.continuing
        # 継続コースの方は卒業生サロンにも参加できるので、alumni も一緒に立てる
        if request.continuing and request.alumni is None:
            patch["alumni"] = True
    if not patch:
        raise HTTPException(status_code=400, detail="変えるものがありません")
    try:
        supabase.table("members").update(patch).eq("id", member_id).execute()
    except Exception:
        # continuing 列をまだ作っていないとき（schema_alumni.sql 未実行）
        if "continuing" not in patch:
            raise
        raise HTTPException(status_code=400,
                            detail="Supabase の SQL Editor で schema_alumni.sql を実行してください")
    return {"ok": True, **patch}


# ---- 全開放（アップセル）----
# 入会直後に1枚だけはさむ。10ヶ月かけて開く分を、今日ぜんぶ開ける、という選択。
# 中身は同じで、届く速さだけが変わる。月々のお支払いはそのまま続く。

UPSELL_PRICE_JPY = int(os.getenv("UPSELL_PRICE_JPY", "49800"))


@app.get("/upsell")
async def upsell_page():
    return FileResponse("static/upsell.html")


@app.get("/api/salon-stats")
async def salon_stats(x_teacher_key: str = Header(None)):
    """サロンの数字。入会数と、そのうち何人が全開放したか。"""
    require_teacher(x_teacher_key)
    members = supabase.table("members").select(
        "tier,active,full_unlock,subscription_started_at").eq("tier", "subscription").execute().data or []
    joined = len(members)
    unlocked = sum(1 for m in members if m.get("full_unlock"))
    active = sum(1 for m in members if m.get("active", True))
    this_month = datetime.now().strftime("%Y-%m")
    joined_this_month = sum(
        1 for m in members if (m.get("subscription_started_at") or "").startswith(this_month))
    return {
        "joined": joined,
        "joined_this_month": joined_this_month,
        "active": active,
        "unlocked": unlocked,
        "unlock_rate": round(unlocked / joined * 100, 1) if joined else 0,
    }


@app.post("/api/upsell-purchase")
async def upsell_purchase(authorization: str = Header(None)):
    """入会時に登録されたカードへ、そのままお支払いいただく（カード再入力なし）。"""
    member = await member_from_token(authorization)
    if member.get("full_unlock"):
        return {"status": "already"}

    customer_id = member.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="お支払い情報が見つかりませんでした。さちえ先生にご連絡ください")

    customer = await stripe_call("GET", f"/customers/{customer_id}")
    card = (customer.get("invoice_settings") or {}).get("default_payment_method")
    if not card:
        cards = await stripe_call("GET", f"/payment_methods?customer={customer_id}&type=card&limit=1")
        found = cards.get("data") or []
        card = found[0]["id"] if found else None
    if not card:
        raise HTTPException(status_code=400, detail="ご登録のカードが見つかりませんでした。さちえ先生にご連絡ください")

    try:
        intent = await stripe_call("POST", "/payment_intents", {
            "amount": str(UPSELL_PRICE_JPY),
            "currency": "jpy",
            "customer": customer_id,
            "payment_method": card,
            "off_session": "true",
            "confirm": "true",
            "description": "Photelier サロン 全開放",
        }, idempotency_key=f"upsell-{member['id']}")
    except HTTPException:
        raise HTTPException(status_code=402,
                            detail="カードでのお支払いができませんでした。カード会社の確認が必要かもしれません。")

    if intent.get("status") != "succeeded":
        raise HTTPException(status_code=402, detail="お支払いが完了しませんでした。もう一度お試しください。")

    supabase.table("members").update({"full_unlock": True}).eq("email", member["email"]).execute()
    return {"status": "ok"}


# ---- お支払いとお手続き（Stripe のお客様ポータル）----
# 退会・カードの変更・領収書の発行を、会員さんご自身でしていただくための入口。
# ここが無いと、その全部がさちえ先生への個別連絡になってしまう。
# 画面は Stripe 側が用意してくれるので、こちらは行き先の URL を作って渡すだけ。

@app.post("/api/billing-portal")
async def billing_portal(request: Request, authorization: str = Header(None)):
    member = await member_from_token(authorization)
    customer_id = member.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400,
                            detail="お支払い情報が見つかりませんでした。お手数ですが、さちえ先生にご連絡ください")
    base = str(request.base_url).rstrip("/")
    try:
        session = await stripe_call("POST", "/billing_portal/sessions", {
            "customer": customer_id,
            "return_url": f"{base}/",
        })
    except HTTPException:
        # Stripe 管理画面でお客様ポータルがまだ有効になっていないと、ここに来る
        raise HTTPException(status_code=503,
                            detail="お手続きの画面をご用意できませんでした。"
                                   "お手数ですが、さちえ先生にご連絡ください")
    return {"url": session["url"]}


# ---- 月1回の質問会アーカイブ ----
# カリキュラム動画（video_library.json）と違って毎月増えていくので、
# さちえ先生が先生ページから1行足すだけで並ぶようにする。
# 入会した月に関係なく、全員がすべての回を見られる。

class QaSessionRequest(BaseModel):
    held_on: str
    title: str
    vimeo_id: str
    vimeo_h: Optional[str] = None
    note: Optional[str] = None


@app.get("/api/qa-sessions")
async def list_qa_sessions(authorization: str = Header(None),
                           x_teacher_key: str = Header(None),
                           student_name: str = None):
    # 動画のIDが入っているので、動画教材と同じく会員だけに渡す。
    # 質問会はPhotelierサロンの場（2026-10-30 本人指示）。
    # 本講座の方（受講生・卒業生・既存6名）には空を返す＝タイル自体が出ない。
    # 本講座には水曜リアルセミナーのアーカイブがある（動画教材の「リアルセミナー」）。
    if not is_teacher(x_teacher_key):
        legacy_pass = legacy_pass_from_auth(authorization)
        if legacy_pass is not None:
            if not is_legacy_ok(student_name, legacy_pass):
                raise HTTPException(status_code=401, detail="合言葉が必要です")
            return {"sessions": [], "ready": True}
        member = await member_from_token(authorization)
        if member["tier"] != "subscription":
            return {"sessions": [], "ready": True}
    try:
        rows = supabase.table("qa_sessions").select("*").order(
            "held_on", desc=True).execute().data or []
    except Exception:
        # まだ Supabase に表を作っていないとき。動画教材まで止めない。
        return {"sessions": [], "ready": False}
    return {"sessions": rows, "ready": True}


@app.post("/api/qa-sessions")
async def add_qa_session(request: QaSessionRequest, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    vimeo_id = request.vimeo_id.strip().rstrip("/").split("/")[-1]
    if not vimeo_id.isdigit():
        raise HTTPException(status_code=400, detail="Vimeoの動画IDは数字です（URLの最後の数字）")
    row = supabase.table("qa_sessions").insert({
        "held_on": request.held_on,
        "title": request.title.strip(),
        "vimeo_id": vimeo_id,
        "vimeo_h": (request.vimeo_h or "").strip() or None,
        "note": (request.note or "").strip() or None,
    }).execute().data
    return {"status": "ok", "session": row[0] if row else None}


@app.delete("/api/qa-sessions/{session_id}")
async def delete_qa_session(session_id: int, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    supabase.table("qa_sessions").delete().eq("id", session_id).execute()
    return {"status": "ok"}


# ---- 卒業生サロンのアーカイブ ----
# 月初金曜のライブ添削の録画。今まではLINEで送っていた（2026-10-30 本人決定でアプリへ）。
# 見せ方の線:
#   卒業生（members.alumni = true）… 全部の回
#   受講中の方（tier = course）    … 最新の1回だけ（「こんな感じなら入ろう」の入口）
#   サロン（tier = subscription）  … 出さない（卒業生サロンは本講座を修了した方の場）
# 全部を無料側に置くと卒業生サロンに入る理由が消えるので、絞るのは必ずここサーバー側で。

class AlumniSessionRequest(BaseModel):
    held_on: str
    title: str
    vimeo_id: str
    vimeo_h: Optional[str] = None
    note: Optional[str] = None


@app.get("/api/alumni-sessions")
async def list_alumni_sessions(authorization: str = Header(None),
                               x_teacher_key: str = Header(None),
                               student_name: str = None):
    if is_teacher(x_teacher_key):
        scope = "all"
    else:
        legacy_pass = legacy_pass_from_auth(authorization)
        if legacy_pass is not None:
            # 既存6名（お名前＋合言葉）。受講中の方と同じ扱い＝最新の1回だけ。
            if not is_legacy_ok(student_name, legacy_pass):
                raise HTTPException(status_code=401, detail="合言葉が必要です")
            scope = "latest"
        else:
            member = await member_from_token(authorization)
            if member["tier"] != "course":
                return {"sessions": [], "scope": "none", "total": 0, "ready": True}
            scope = "all" if member.get("alumni") else "latest"
    try:
        rows = supabase.table("alumni_sessions").select("*").order(
            "held_on", desc=True).execute().data or []
    except Exception:
        # まだ schema_alumni.sql を実行していないとき。動画教材まで止めない。
        return {"sessions": [], "scope": scope, "total": 0, "ready": False}
    total = len(rows)
    if scope == "latest":
        rows = rows[:1]
    return {"sessions": rows, "scope": scope, "total": total, "ready": True}


@app.post("/api/alumni-sessions")
async def add_alumni_session(request: AlumniSessionRequest, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    vimeo_id = request.vimeo_id.strip().rstrip("/").split("/")[-1]
    if not vimeo_id.isdigit():
        raise HTTPException(status_code=400, detail="Vimeoの動画IDは数字です（URLの最後の数字）")
    row = supabase.table("alumni_sessions").insert({
        "held_on": request.held_on,
        "title": request.title.strip(),
        "vimeo_id": vimeo_id,
        "vimeo_h": (request.vimeo_h or "").strip() or None,
        "note": (request.note or "").strip() or None,
    }).execute().data
    return {"status": "ok", "session": row[0] if row else None}


@app.delete("/api/alumni-sessions/{session_id}")
async def delete_alumni_session(session_id: int, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    supabase.table("alumni_sessions").delete().eq("id", session_id).execute()
    return {"status": "ok"}


# ---- 質問会の日程 ----
# 毎月 第4金曜 21:00。12月だけは第4金曜がクリスマス前後に当たるので第3金曜。
# 初回は 2026/9/18。8/28（第4金曜）は1dayレッスンの日なので質問会はやらない。
# 日程の決まりはここにだけ書く。画面はこの API から受け取る。

QA_FIRST = date(2026, 9, 18)
QA_DEADLINE_DAYS = 3          # 開催の3日前で締め切る（準備の時間を取るため）

# 質問会のzoomの部屋。毎回おなじ部屋を使う（定期ミーティング・期限なし）。
# 部屋を作りなおしたときは、この1行だけ書き換える。
# このURLは、ログインしている会員さんの画面にだけ出す。
QA_ZOOM_URL = "https://us02web.zoom.us/j/86947628346?pwd=5dbZMfks8X6VpWIYssAxs4fJZDRa1z.1"

# 本講座のリアルセミナー（基本は毎週水曜 10:00〜12:00）のzoomの部屋。
# 受講生の画面にだけ出る。URLが決まったら、この1行に貼る（空のままなら、ボタンは出ない）。
SEMINAR_ZOOM_URL = "https://us02web.zoom.us/j/7103987614?pwd=YlNoTTd1TlRlOFhjd2QydXVYa0VGdz09&omn=86751484388"

# 卒業生サロン（毎月 月初=第1金曜の午前）のzoomの部屋。毎回おなじ部屋。
# 卒業生（members.alumni = true）の画面にだけ出す。
ALUMNI_ZOOM_URL = "https://us02web.zoom.us/j/83052981573?pwd=Zmx2V092TytkeVRieEZwNWx6VEk5Zz09"
ALUMNI_TIME = "10:00"   # 開始時間。変わったらここだけ書き換える（さちえ先生に確認して入れた値）

# 卒業生サロンで、その月だけ日をずらしたいとき。{(年, 月): 開催日}
ALUMNI_OVERRIDES = {
    (2027, 1): date(2027, 1, 8),  # 第1金曜が元日(1/1)なので次の週へ。2026-10-30 本人指示
}

# 質問会で、その月だけ日をずらしたいとき。{(年, 月): 開催日}
# 用が済んだ行は消さずに残しておくと、あとから「あの月はいつだったか」を追える。
QA_OVERRIDES = {
    (2026, 9): date(2026, 9, 18),   # 初回。第4金曜(9/25)はさちえ先生に先約があるため1週間前倒し
    (2026, 10): date(2026, 10, 30), # 第4金曜(10/23)から1週間後ろへ。2026-10-14 本人決定
}


def qa_session_date(year: int, month: int) -> date:
    """その月の質問会の日。12月だけ第3金曜、ほかは第4金曜。"""
    if (year, month) in QA_OVERRIDES:
        return QA_OVERRIDES[(year, month)]
    nth = 3 if month == 12 else 4
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7        # weekday: 月=0 … 金=4
    return date(year, month, 1 + offset + (nth - 1) * 7)


def next_qa_date(today: Optional[date] = None) -> date:
    """次に開かれる質問会の日。当日はまだ「次」として扱う。"""
    today = today or date.today()
    y, m = today.year, today.month
    for _ in range(14):
        d = qa_session_date(y, m)
        if d >= today and d >= QA_FIRST:
            return d
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return QA_FIRST


def alumni_session_date(year: int, month: int) -> date:
    """その月の卒業生サロンの日。月初＝第1金曜。"""
    if (year, month) in ALUMNI_OVERRIDES:
        return ALUMNI_OVERRIDES[(year, month)]
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7        # weekday: 月=0 … 金=4
    return date(year, month, 1 + offset)


def next_alumni_date(today: Optional[date] = None) -> date:
    """次の卒業生サロンの日。当日はまだ「次」として扱う。"""
    today = today or date.today()
    y, m = today.year, today.month
    for _ in range(14):
        d = alumni_session_date(y, m)
        if d >= today:
            return d
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return alumni_session_date(today.year, today.month)


def qa_accepting_for(today: Optional[date] = None) -> date:
    """今いただいた質問を、どの回で扱うか。締切を過ぎていたら次の回に回す。"""
    today = today or date.today()
    d = next_qa_date(today)
    if (d - today).days < QA_DEADLINE_DAYS:
        return next_qa_date(d + timedelta(days=1))
    return d


@app.get("/api/qa-next")
async def qa_next(authorization: str = Header(None)):
    accepting = qa_accepting_for()
    result = {
        "next": next_qa_date().isoformat(),
        "accepting_for": accepting.isoformat(),
        "deadline": (accepting - timedelta(days=QA_DEADLINE_DAYS)).isoformat(),
    }
    # zoomのURLは、在籍中の会員さんにだけ渡す。
    # ログインしていない人には日付だけ返す（画面が止まらないように）。
    try:
        member = await member_from_token(authorization)
        result["zoom_url"] = QA_ZOOM_URL
        # 水曜リアルセミナーは受講中の方の場。卒業生にはURL自体を渡さない。
        # 継続コースの方（alumni かつ continuing）は水曜にも出るので渡す。
        if SEMINAR_ZOOM_URL and not hides_seminar(member):
            result["seminar_zoom_url"] = SEMINAR_ZOOM_URL
        # 卒業生には、卒業生サロン（月初金曜）の日程とzoomを返す
        if member.get("alumni"):
            result["alumni_next"] = next_alumni_date().isoformat()
            result["alumni_time"] = ALUMNI_TIME
            result["alumni_zoom_url"] = ALUMNI_ZOOM_URL
    except HTTPException:
        pass
    return result


# ---- 質問会の事前質問 ----
# 会員さんがサロンの中から質問を送る。さちえ先生は先生ページでまとめて読む。

class QuestionRequest(BaseModel):
    body: str


@app.post("/api/questions")
async def add_question(request: QuestionRequest, authorization: str = Header(None)):
    member = await member_from_token(authorization)
    body = request.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="質問の内容を入れてください")
    if len(body) > 1000:
        raise HTTPException(status_code=400, detail="1000文字まででお願いします")
    try:
        supabase.table("qa_questions").insert({
            "email": member["email"],
            "name": member.get("name") or member["email"],
            "body": body,
            "for_session": qa_accepting_for().isoformat(),
        }).execute()
    except Exception:
        # まだ Supabase に表を作っていないとき
        raise HTTPException(status_code=503, detail="いま質問をお預かりできませんでした。少ししてからもう一度お試しください。")
    return {"status": "ok", "for_session": qa_accepting_for().isoformat()}


@app.get("/api/my-questions")
async def my_questions(authorization: str = Header(None)):
    """自分が送った質問だけ。二重に送ってしまうのを防ぐため。"""
    member = await member_from_token(authorization)
    try:
        rows = supabase.table("qa_questions").select("*").eq(
            "email", member["email"]).gte(
            "for_session", date.today().isoformat()).order(
            "created_at").execute().data or []
    except Exception:
        # まだ Supabase に表を作っていないとき。ホーム画面まで止めない。
        return {"questions": [], "ready": False}
    return {"questions": rows, "ready": True}


@app.get("/api/questions")
async def list_questions(x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    try:
        rows = supabase.table("qa_questions").select("*").order(
            "for_session", desc=True).order("created_at").execute().data or []
    except Exception:
        return {"questions": [], "ready": False}
    return {"questions": rows, "ready": True}


@app.patch("/api/questions/{question_id}")
async def mark_question(question_id: int, answered: bool = True,
                        x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    supabase.table("qa_questions").update(
        {"answered": answered}).eq("id", question_id).execute()
    return {"status": "ok"}


# ---- サロンのお知らせ ----
# 全員に伝えたいこと（質問会の日程、リアルイベントの案内など）を置く場所。
# 在籍している人にだけ届く。みんなの部屋（オープンチャット）は
# 写真を出し合う場で、こちらは連絡の場。役割を分けている。

class AnnouncementRequest(BaseModel):
    title: str
    body: str
    audience: str = "all"   # all=みなさん / salon=サロン会員だけ / course=受講生だけ


@app.get("/api/announcements")
async def list_announcements(authorization: str = Header(None)):
    """会員さん向け。新しいものから5件だけ返す。
    質問会はサロン、リアルセミナーは本講座のもの。宛先の違うお知らせは出さない。"""
    member = await member_from_token(authorization)
    mine = "salon" if member["tier"] == "subscription" else "course"
    try:
        rows = supabase.table("announcements").select("*").in_(
            "audience", ["all", mine]).order(
            "created_at", desc=True).limit(5).execute().data or []
    except Exception:
        # まだ Supabase に表を作っていない／audience の列がまだないとき。
        # ホーム画面を止めたくないので、宛先なしで出す。
        try:
            rows = supabase.table("announcements").select("*").order(
                "created_at", desc=True).limit(5).execute().data or []
        except Exception:
            return {"announcements": [], "ready": False}
    return {"announcements": rows, "ready": True}


@app.post("/api/announcements")
async def add_announcement(request: AnnouncementRequest,
                           x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    title = request.title.strip()
    body = request.body.strip()
    if not title or not body:
        raise HTTPException(status_code=400, detail="タイトルと本文を入れてください")
    audience = request.audience if request.audience in ("all", "salon", "course") else "all"
    try:
        supabase.table("announcements").insert(
            {"title": title, "body": body, "audience": audience}).execute()
    except Exception:
        # まだ Supabase に表を作っていないとき
        raise HTTPException(status_code=503, detail="お知らせの置き場所（announcements）がまだありません。Supabase の SQL Editor で schema_announcements.sql を実行してください。")
    return {"status": "ok"}


@app.delete("/api/announcements/{announcement_id}")
async def delete_announcement(announcement_id: int,
                              x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    supabase.table("announcements").delete().eq("id", announcement_id).execute()
    return {"status": "ok"}


@app.get("/api/announcements/all")
async def list_announcements_all(x_teacher_key: str = Header(None)):
    """先生ページ用。過去のものも全部。"""
    require_teacher(x_teacher_key)
    try:
        rows = supabase.table("announcements").select("*").order(
            "created_at", desc=True).execute().data or []
    except Exception:
        return {"announcements": [], "ready": False}
    return {"announcements": rows, "ready": True}


# ---- みんなの部屋（LINEオープンチャット）----
# オープンチャットは匿名で参加できる仕組みなので、参加者一覧には
# 「その部屋用の表示名」しか出ない。本名もメールアドレスも見えない。
# そのままだと、退会された方がどの人か分からず、部屋に残り続けてしまう。
#
# なので「部屋で使うお名前」を先に教えていただき、保存してから参加コードを出す。
# これで「お申し込みの方」と「部屋の表示名」が1対1でつながり、
# 月に1回、退会された方を名簿で探して外していただける。
#
# URLと参加コードは環境変数。まだ部屋を作っていないうちは空でよく、
# そのときはこの案内ごと画面に出ない（壊れない）。
#
# みんなの部屋は「サロンの方だけ」の場所。本講座の方には出さない。

OPENCHAT_URL = os.getenv("OPENCHAT_URL", "").strip()
OPENCHAT_CODE = os.getenv("OPENCHAT_CODE", "").strip()


class OpenchatNameRequest(BaseModel):
    name: str


def openchat_missing_column():
    return HTTPException(
        status_code=503,
        detail="みんなの部屋のお名前を保存する場所（members.openchat_name）がまだありません。"
               "Supabase の SQL Editor で schema_openchat.sql を実行してください。")


def is_salon(member: dict) -> bool:
    """みんなの部屋は、サロンの方だけの場所。本講座の方には出さない。"""
    return member.get("tier") == "subscription"


@app.get("/api/openchat")
async def openchat_info(authorization: str = Header(None)):
    """みんなの部屋の案内。お名前を出していただくまで、参加コードは返さない。"""
    member = await member_from_token(authorization)
    if not OPENCHAT_URL or not OPENCHAT_CODE or not is_salon(member):
        # まだ部屋を作っていない、または本講座の方。画面ごと出さない。
        return {"ready": False}
    name = (member.get("openchat_name") or "").strip()
    if not name:
        return {"ready": True, "name": None}
    return {"ready": True, "name": name, "url": OPENCHAT_URL, "code": OPENCHAT_CODE}


@app.post("/api/openchat")
async def openchat_set_name(request: OpenchatNameRequest,
                            authorization: str = Header(None)):
    """部屋で使うお名前を預かって、参加コードをお返しする。"""
    member = await member_from_token(authorization)
    if not OPENCHAT_URL or not OPENCHAT_CODE:
        raise HTTPException(status_code=503, detail="みんなの部屋は、いま準備中です")
    if not is_salon(member):
        raise HTTPException(status_code=403, detail="みんなの部屋は、サロンの方の場所です")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="お名前を入れてください")
    if len(name) > 30:
        raise HTTPException(status_code=400, detail="お名前は30文字までにしてください")

    try:
        supabase.table("members").update(
            {"openchat_name": name}).eq("email", member["email"]).execute()
    except Exception:
        raise openchat_missing_column()

    return {"status": "ok", "name": name, "url": OPENCHAT_URL, "code": OPENCHAT_CODE}


@app.post("/api/password-reset")
async def password_reset(request: Request, body: PasswordResetRequest):
    """パスワード再発行メールを Supabase から送る。さちえ先生の手はかからない。
    メールのリンクを押すと /reset-password（新しいパスワードを決める画面）に着く。"""
    base = str(request.base_url).rstrip("/")
    redirect_to = f"{base}/reset-password"
    async with httpx.AsyncClient(timeout=15) as http:
        await http.post(
            f"{SUPABASE_URL}/auth/v1/recover",
            params={"redirect_to": redirect_to},  # Supabase は本文ではなくURLのクエリを見る
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
            json={"email": body.email.strip().lower(),
                  "redirect_to": redirect_to},
        )
    # 登録の有無は返さない（メールアドレスの存在確認に使われないように）
    return {"status": "ok"}


@app.get("/reset-password")
async def reset_password_page():
    """メールのリンクの着地点。新しいパスワードを決めてもらう。"""
    return FileResponse("static/reset-password.html")


class PasswordUpdateRequest(BaseModel):
    access_token: str
    password: str


@app.post("/api/password-update")
async def password_update(body: PasswordUpdateRequest):
    """新しいパスワードを保存する。
    メールのリンクに付いてくる合言葉（access_token）を持っている人だけが通る。
    このアプリの鍵（SUPABASE_KEY）はブラウザに渡さないので、ここを経由させている。"""
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="パスワードは8文字以上にしてください")
    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.put(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_KEY,
                     "Authorization": f"Bearer {body.access_token}",
                     "Content-Type": "application/json"},
            json={"password": body.password},
        )
    if res.status_code >= 400:
        print(f"❌ パスワード更新エラー: {res.text}")
        raise HTTPException(
            status_code=400,
            detail="このリンクは期限切れか、すでに使われています。"
                   "お手数ですが、ログイン画面の「パスワードを忘れた方」からもう一度お試しください")
    return {"email": res.json().get("email", "")}


@app.get("/api/status/{student_name}")
async def get_status(student_name: str, authorization: str = Header(None),
                     x_teacher_key: str = Header(None)):
    await require_owner(student_name, authorization, x_teacher_key)
    student_info = get_student_info(student_name)
    monthly_count = get_monthly_count(student_name)
    remaining = max(0, MONTHLY_LIMIT - monthly_count)

    end_date = None
    is_expired = False
    if student_info and student_info.get("end_date"):
        end_date = student_info["end_date"]
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        is_expired = datetime.now() > end_dt

    course_months = 6
    if student_info and student_info.get("course_months"):
        course_months = student_info["course_months"]

    sessions_remaining = None
    sessions_deadline = None
    if student_info and student_info.get("sessions_remaining") is not None:
        sessions_remaining = student_info["sessions_remaining"]
    if student_info and student_info.get("sessions_deadline"):
        sessions_deadline = student_info["sessions_deadline"]

    return {
        "monthly_remaining": remaining,
        "monthly_limit": MONTHLY_LIMIT,
        "end_date": end_date,
        "is_expired": is_expired,
        "course_months": course_months,
        "sessions_remaining": sessions_remaining,
        "sessions_deadline": sessions_deadline
    }

@app.post("/api/chat")
async def chat(request: ChatRequest, authorization: str = Header(None)):
    if not request.student_name or not request.message:
        raise HTTPException(status_code=400, detail="名前とメッセージが必要です")
    await require_owner(request.student_name, authorization)

    student_info = get_student_info(request.student_name)
    if student_info and student_info.get("end_date"):
        end_dt = datetime.strptime(student_info["end_date"], "%Y-%m-%d")
        if datetime.now() > end_dt:
            def expired_gen():
                msg = "サポート期間が終了しています😊\nまた一緒に学びたい場合は、さちえ先生に直接ご連絡ください✨"
                yield f"data: {json.dumps({'text': msg}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
            return StreamingResponse(expired_gen(), media_type="text/event-stream")

    monthly_count = get_monthly_count(request.student_name)
    if monthly_count >= MONTHLY_LIMIT:
        def limit_gen():
            msg = f"今月はもう{MONTHLY_LIMIT}件質問してくれたよ😊✨\n来月また一緒に頑張ろうね！引き続き課題頑張って！📸"
            yield f"data: {json.dumps({'text': msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        return StreamingResponse(limit_gen(), media_type="text/event-stream")

    increment_monthly_count(request.student_name)

    history = load_conversation(request.student_name)

    if request.image:
        user_content = [
            {"type": "text", "text": request.message},
            {"type": "image_url", "image_url": {
                "url": f"data:{request.image_type};base64,{request.image}"
            }}
        ]
        history.append({"role": "user", "content": request.message + " [画像添付]"})
    else:
        user_content = request.message
        history.append({"role": "user", "content": request.message})

    save_conversation(request.student_name, history)

    # 課題リストと提出ボタンがあるのは既存6名だけ（お名前で入る方）。
    # 新しい受講生とサロン会員に「課題リストにチェックを入れてね」と言うと、
    # 画面にないものを探させてしまう。個別セッションの予約も、もうない。
    has_tasks = request.student_name in legacy_names()
    tier_note = "" if has_tasks else """

---

## この方について（大切）

この方の画面には、課題リストも提出ボタンもありません。個別セッションもありません。
- 「課題リストにチェックを入れてね」「提出してね」「予約してね」とは言わないこと
- 撮ってもらいたいときは「撮ったら、ここに写真を送ってくださいね」とお伝えする
- 写真を送ってもらったら、この場でそのまま見て、よいところと直すところを1つずつ返す
"""

    system_message = SYSTEM_PROMPT + VIDEO_GUIDE + tier_note + knowledge_base
    if request.image:
        messages_with_system = [{"role": "system", "content": system_message}] + history[:-1] + [{"role": "user", "content": user_content}]
    else:
        messages_with_system = [{"role": "system", "content": system_message}] + history

    def generate():
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=2048,
                messages=messages_with_system,
                stream=True
            )
            for chunk in stream:
                text = chunk.choices[0].delta.content or ""
                if text:
                    full_response += text
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

            history.append({"role": "assistant", "content": full_response})
            save_conversation(request.student_name, history)
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"❌ エラー発生: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/progress/{student_name}")
async def get_progress(student_name: str, authorization: str = Header(None),
                       x_teacher_key: str = Header(None)):
    await require_owner(student_name, authorization, x_teacher_key)
    try:
        result = supabase.table("progress").select("completed").eq("student_name", student_name).execute()
        if result.data:
            return {"completed": result.data[0]["completed"]}
    except Exception as e:
        print(f"❌ 進捗取得エラー: {e}")
    return {"completed": []}

class ProgressRequest(BaseModel):
    student_name: str
    completed: list

@app.post("/api/progress")
async def update_progress(request: ProgressRequest, authorization: str = Header(None)):
    await require_owner(request.student_name, authorization)
    try:
        supabase.table("progress").upsert({
            "student_name": request.student_name,
            "completed": request.completed
        }).execute()
    except Exception as e:
        print(f"❌ 進捗保存エラー: {e}")
    return {"status": "ok"}

@app.get("/api/video-progress/{student_name}")
async def get_video_progress(student_name: str, authorization: str = Header(None),
                             x_teacher_key: str = Header(None)):
    await require_owner(student_name, authorization, x_teacher_key)
    try:
        result = supabase.table("video_progress").select("watched").eq("student_name", student_name).execute()
        if result.data:
            return {"watched": result.data[0]["watched"]}
    except Exception as e:
        print(f"❌ 動画進捗取得エラー: {e}")
    return {"watched": []}

class VideoProgressRequest(BaseModel):
    student_name: str
    watched: list

@app.post("/api/video-progress")
async def update_video_progress(request: VideoProgressRequest, authorization: str = Header(None)):
    await require_owner(request.student_name, authorization)
    try:
        supabase.table("video_progress").upsert({
            "student_name": request.student_name,
            "watched": request.watched
        }).execute()
    except Exception as e:
        print(f"❌ 動画進捗保存エラー: {e}")
    return {"status": "ok"}

@app.get("/teacher")
async def teacher_page():
    return FileResponse("static/teacher.html")

@app.get("/api/summary/{student_name}")
async def get_summary(student_name: str, x_teacher_key: str = Header(None)):
    require_teacher(x_teacher_key)
    history = load_conversation(student_name)
    if not history:
        return {"summary": None, "last_date": None, "message_count": 0}

    conversation_text = ""
    for msg in history:
        role = "受講生" if msg["role"] == "user" else "AI"
        conversation_text += f"{role}：{msg['content']}\n\n"

    summary_prompt = f"""以下は受講生「{student_name}」さんとAIサポートの会話履歴です。
さちえ先生が個別コンサルの準備をするために、以下の形式で簡潔にまとめてください。

【会話履歴】
{conversation_text}

【まとめ形式】
以下のJSON形式で返してください：
{{
  "悩み": "主な悩みや相談内容を2〜3文で",
  "アドバイス": "AIがした主なアドバイスや方向性を2〜3文で",
  "次のステップ": "提案した次のアクションを1〜2文で",
  "注目ポイント": "さちえ先生が個別コンサルで特に触れるといいポイントを1〜2文で"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=1000,
            messages=[{"role": "user", "content": summary_prompt}],
            response_format={"type": "json_object"}
        )
        summary_data = json.loads(response.choices[0].message.content)
        return {
            "summary": summary_data,
            "message_count": len([m for m in history if m["role"] == "user"]),
            "total_messages": len(history)
        }
    except Exception as e:
        print(f"❌ 要約エラー: {e}")
        return {"summary": None, "message_count": 0, "error": str(e)}

@app.get("/api/conversation/{student_name}")
async def get_conversation(student_name: str, authorization: str = Header(None),
                           x_teacher_key: str = Header(None)):
    await require_owner(student_name, authorization, x_teacher_key)
    history = load_conversation(student_name)
    return {"messages": history, "count": len(history)}

@app.post("/api/reset")
async def reset_conversation(request: ResetRequest, authorization: str = Header(None)):
    await require_owner(request.student_name, authorization)
    try:
        supabase.table("conversations").delete().eq("student_name", request.student_name).execute()
    except Exception as e:
        print(f"❌ リセットエラー: {e}")
    return {"status": "ok"}

class SubmissionRequest(BaseModel):
    student_name: str
    assignment_name: str
    content: str
    image: Optional[str] = None
    url: Optional[str] = None

@app.post("/api/submit")
async def submit_assignment(request: SubmissionRequest, authorization: str = Header(None)):
    # 写真を出せるのは、本講座・継続コース・卒業生サロンの方（tier='course'）と、
    # お名前で入る既存6名（2026-11-04 本人指示）。
    # Photelierサロンの方には添削がないので、ここで止める
    # （画面にボタンを出さないだけでは、直接呼べば通ってしまうため）。
    if "@" in (request.student_name or ""):
        member = await member_from_token(authorization)
        if member["email"].strip().lower() != request.student_name.strip().lower():
            raise HTTPException(status_code=403, detail="ほかの方のデータは見られません")
        if member.get("tier") != "course":
            raise HTTPException(status_code=403,
                                detail="写真の提出は、本講座・卒業生サロンの方の機能です")
    else:
        await require_owner(request.student_name, authorization)
    try:
        supabase.table("submissions").insert({
            "student_name": request.student_name,
            "assignment_name": request.assignment_name,
            "content": request.content,
            "image_data": request.image,
            "url": request.url,
            "submitted_at": datetime.now().isoformat()
        }).execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ 提出エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/submissions/{student_name}")
async def get_submissions(student_name: str, authorization: str = Header(None),
                          x_teacher_key: str = Header(None)):
    await require_owner(student_name, authorization, x_teacher_key)
    try:
        result = supabase.table("submissions").select("*").eq("student_name", student_name).order("submitted_at", desc=True).execute()
        return {"submissions": result.data}
    except Exception as e:
        print(f"❌ 提出物取得エラー: {e}")
        return {"submissions": []}

@app.get("/api/all-submissions")
async def get_all_submissions(x_teacher_key: str = Header(None), limit: int = 100):
    """写真の提出を、新しい順に。水曜のセミナーで上から順に見ていくための一覧。
    ★ 写真そのものは入れない（1枚3〜8MBあるので、全部入れると画面が開かなくなる）。
      写真は一覧に並んだあと、1件ずつ /api/submission/{id} で取りに行く。
    ★ 写真の提出だけを出す。受講生の画面を共有しながら添削するので、
      テキストの課題（ペルソナ設定など）が混ざらないようにしている（2026-11-04 本人）。"""
    require_teacher(x_teacher_key)
    cols = "id,student_name,assignment_name,content,url,submitted_at"
    for extra in (",annotated_at", ""):
        try:
            result = (supabase.table("submissions").select(cols + extra)
                      .eq("assignment_name", "写真提出")
                      .order("submitted_at", desc=True).limit(limit).execute())
            rows = result.data
            # メールで入る方の student_name はメールアドレスなので、お名前に直して並べる。
            # あわせて「本講座／卒業生サロン」の別も付ける
            # （添削のときに探さなくていいように / 2026-11-04 本人）。
            # ★ 継続コースの方は本講座と一緒でよい（2026-11-04 本人）。
            info = {}
            try:
                sel = "email,name,alumni,continuing"
                for c in (sel, "email,name,alumni", "email,name"):
                    try:
                        members = supabase.table("members").select(c).execute()
                        break
                    except Exception:
                        continue
                info = {m["email"]: m for m in (members.data or [])}
            except Exception as e:
                print(f"⚠ 会員情報の取得に失敗（メールのまま表示します）: {e}")
            for r in rows:
                key = (r.get("student_name") or "").strip().lower()
                m = info.get(key)
                if m:
                    r["student_name"] = m["name"]
                    r["group"] = ("卒業生サロン"
                                  if m.get("alumni") and not m.get("continuing")
                                  else "本講座")
                else:
                    r["group"] = "本講座"   # お名前で入る既存6名
            return {"submissions": rows}
        except Exception as e:
            err = e
    print(f"❌ 全提出物取得エラー: {err}")
    return {"submissions": []}


@app.get("/api/submission/{submission_id}")
async def get_submission(submission_id: int, x_teacher_key: str = Header(None)):
    """1件ぶんの写真（元・添削後）を取り出す。"""
    require_teacher(x_teacher_key)
    try:
        result = (supabase.table("submissions").select("*")
                  .eq("id", submission_id).limit(1).execute())
        if not result.data:
            raise HTTPException(status_code=404, detail="見つかりませんでした")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 提出物1件の取得エラー: {e}")
        raise HTTPException(status_code=500, detail="読み込めませんでした")


class AnnotateRequest(BaseModel):
    image: str   # 線を書いたあとの写真（base64・data: のヘッダは外して送る）


@app.post("/api/submissions/{submission_id}/annotate")
async def save_annotation(submission_id: int, request: AnnotateRequest,
                          x_teacher_key: str = Header(None)):
    """添削後の写真を保存する。元の写真（image_data）はそのまま残す
    ＝ ビフォーアフターの2枚が手元に残る（2026-10-06 本人決定）。"""
    require_teacher(x_teacher_key)
    try:
        supabase.table("submissions").update({
            "annotated_image": request.image,
            "annotated_at": datetime.now().isoformat(),
        }).eq("id", submission_id).execute()
        return {"ok": True}
    except Exception as e:
        print(f"❌ 添削の保存エラー: {e}")
        raise HTTPException(status_code=500,
                            detail="保存できませんでした。Supabase の SQL は実行済みでしょうか")

# ---- 発信ネタ出しツール（本講座の受講生だけ） ----
# サロン会員（tier='subscription'）には出さない。
# 期限はアプリのログイン期間そのもの（active=false でここも使えなくなる）。

async def course_member_from_token(authorization: Optional[str]) -> dict:
    member = await member_from_token(authorization)
    if member.get("tier") != "course":
        raise HTTPException(status_code=403, detail="こちらは本講座の受講生の方向けのツールです😊")
    return member


# 工程ごとの参考動画。video_library.json と同じ Vimeo ID + 限定公開ハッシュ。
# static には置かない（ログインした本講座の受講生だけが API 経由で受け取る）。
HASSHIN_VIDEOS = {
    "zero": [
        {"label": "マーケティング全体像の把握", "url": "https://vimeo.com/1143041543/bf9d8ced75"},
        {"label": "ブランディングとマーケティングの違い", "url": "https://vimeo.com/1148047603/267cd0f902"},
    ],
    "zero2": [
        {"label": "売れる市場", "url": "https://vimeo.com/1143044424/bcc22fab5b"},
        {"label": "リサーチ・モデリング", "url": "https://vimeo.com/1143264618/4e4072e15c"},
    ],
    "karte": [
        {"label": "ペルソナ設定", "url": "https://vimeo.com/1143047013/73336d5b46"},
        {"label": "解決策", "url": "https://vimeo.com/1148009088/2327c6c67f"},
        {"label": "コンセプト設計", "url": "https://vimeo.com/1143051495/fb61d7014e"},
    ],
    "profile": [
        {"label": "インスタプロフィール", "url": "https://vimeo.com/1143054115/8eb7b641d0"},
    ],
    "weekly": [
        {"label": "発信の本質", "url": "https://vimeo.com/1143270042/f0804f82f8"},
        {"label": "発信ネタ出し・7つの型", "url": "https://vimeo.com/1143270964/28ffdc0649"},
    ],
    "cards": [
        {"label": "5つの発信テンプレート", "url": "https://vimeo.com/1144392445/304544d478"},
        {"label": "ストーリーズ投稿", "url": "https://vimeo.com/1148058561/b79a22ea00"},
        {"label": "リール作成", "url": "https://vimeo.com/1143272914/93282708ff"},
    ],
    "destination": [
        {"label": "満席を作るLINE告知文", "url": "https://vimeo.com/1144424590/fa4e4161f6"},
        {"label": "お申し込みを頂く流れ", "url": "https://vimeo.com/1067557033/ce32fcd178"},
    ],
}

# さちえ先生の注意事項を「仕組みで守らせる」部分。ここがツールの価値の本体。
HASSHIN_BASE_PROMPT = """あなたはPhotelier Academyのさちえ先生の「発信ネタ出しツール」の中のAIです。
相手はお教室の先生・ハンドメイド作家・フォトグラファーなどの受講生（ママが多い）です。

全モード共通で必ず守ること:
- やさしい敬語。煽らない（「今しかない」「早くしないと」等は禁止）
- 期限の約束をしない（「3ヶ月で申し込みが来る」等は書かない。書くなら事実だけ「反応は貯まった本数で変わります」）
- 商品設計・価格には触れない（受講生はレッスン・作品を既に持っている。高額化は教えない）
- マーケティング用語を使わない（ペルソナ→お客さま、導線→行き先、CTA→ご案内 と言い換える）
- 受講生を責めない。できていないことを指摘する言い方をしない
"""

HASSHIN_MODE_PROMPTS = {
    # ⓪ なんのサービスにするか決める（対話）
    "zero": HASSHIN_BASE_PROMPT + """
今は「なんのサービスにするか決める」対話です。発信が止まるのは迷っているから。あなたの仕事は絞る手伝いです。

ルール:
- ★未来を聞かない。過去の事実だけ聞く（「何がやりたいですか」はふんわりが返るので禁止。「誰に、何て言われましたか？」は事実しか返らない）
- 聞くことは3つだけ: ①実際に人に喜ばれたのはどれか（誰に何て言われたか） ②お金や時間をかけ続けているのはどれか ③なぜそれを始めたのか（想いの強さ）
- 1回の返事で質問は1つだけ。短く
- 選ばなかったものは「やめる」ではなく「後に回す」と言う（捨てられないから止まる人が多い）
- 事実が2つ以上揃って軸が1つに絞れたら decided を true にする

必ずこのJSONだけを返す:
{"reply": "次の質問または相づち（短く）", "decided": false, "axis": "", "later": [], "summary": ""}
decided が true のとき: axis=軸にするもの1つ、later=後に回すもの、summary=「軸は◯◯。△△は後に回す。やめなくて大丈夫です」の形の一言
""",
    # ⓪-2 売れる市場との掛け合わせ案
    "market": HASSHIN_BASE_PROMPT + """
受講生のサービスの軸を「売れる市場」5ジャンル（①ビジネス・仕事 ②お金 ③美容・健康 ④恋愛・人間関係・子育て・自己肯定感 ⑤スピリチュアル）と掛け合わせた案を3つ出します。
受講生は「自分の経験があって、言いやすいもの」を選びます。

必ずこのJSONだけを返す:
{"options": [{"market": "市場名（例: 癒し・自己肯定感）", "idea": "掛け合わせの一言（例: 無心になれる、大人のバレエ塗り絵時間）"}, ...3つ],
 "search_words": ["Instagramで検索する言葉を2つ"],
 "ato_hint": "売れた跡を見る場所の一言（お仕事のタイプに合わせる: 募集型=ストアカ等/物販型=メルカリ・minne/受注型=同業の実績ページ。同じものが無ければ隣を見ればOKと添える）"}
""",
    # ⓪-2 出口: サービス決定の1文
    "service": HASSHIN_BASE_PROMPT + """
ニーズ確認の結果から「この形のサービスにする」の1文を作ります。
形は必ず「（悩みの言葉）な（お客さま）へ、（何を・どんな形で）お届けする」。

必ずこのJSONだけを返す:
{"sentence": "1文", "note": "形は発信への反応を見て、あとから育てられます"}
""",
    # ① カルテ: 悩み候補（1段目・ざっくり5つ）
    "nayami": HASSHIN_BASE_PROMPT + """
お客さま像とサービスから、そのお客さまの悩みの候補を5つ出します。
受講生に白紙で書かせないための候補です。exclude に入っているものと同じ・似たものは出さない。

必ずこのJSONだけを返す:
{"options": ["悩みを短い一言で", ...5つ]}
""",
    # ① カルテ: 悩みを場面の言葉に（2段目・3つ）
    "nayami_scene": HASSHIN_BASE_PROMPT + """
選ばれた悩みを「具体的な場面の言葉」に展開します（裏で100個出して良い3つだけ見せるイメージ）。
例:「独学で自信がない」→「レシピ通りやったのに、アイシングがにじむ」。
発信の1行目に使えるのは場面の言葉だけです。本人の口から出たような、生活の中の一場面にする。
exclude に入っているものと同じ・似たものは出さない。

必ずこのJSONだけを返す:
{"options": ["場面の言葉", ...3つ]}
""",
    # ①-2 プロフィール4行
    "profile": HASSHIN_BASE_PROMPT + """
カルテからインスタのプロフィール文を作ります。4つの役割に固定:
1行目=何の専門家か（コンセプト1行。解決できることから） 2行目=誰向けか 3行目=できること・実績 最後=行き先への一言（例: 体験レッスンはこちら↓）。
全体で5〜6行まで。絵文字は1〜2個まで。

必ずこのJSONだけを返す:
{"lines": ["行", ...]}
""",
    # ② → ③ 7本のネタ
    "neta": HASSHIN_BASE_PROMPT + """
カルテと「いま作っているもの（一言テーマ）」から、1週間分=7本の発信ネタを出します。
7つの型: ①理想の未来 ②あなたにもできる ③学びになること ④人柄 ⑤実績・つよみ ⑥ご案内 ⑦背中を押す

必ず守ること（さちえ先生のルール）:
- 7つの型を1本ずつ、全部使う（③ノウハウに寄らせない。再生数だけ伸びても申し込みにつながらないから）
- ⑥ご案内を1本目と最後にしない。前後がご案内にならない位置（間に入れ込むと売り込み感が消える）
- ④人柄は必ずストーリーズに振る（プライベート写真で世界観が崩れないように）
- ⑤実績には note に「この投稿は再生数は伸びません。でも信頼のために必要な1本です」を入れる
- 1本目（まずはこれ）の hook は、カルテの「場面の悩み」の言葉から始める（「私のことだ」になる）
- ⑥ご案内はカルテの「解決できること」と「行き先」から作る（売り込みにならない）
- ②あなたにもできる・⑦背中を押すは、カルテの「きっかけと変化」の実話から作る（テンプレ感が消える）
- 撮るものは1本につき1つだけ、具体的に。★dest に合わせる: フィード/ストーリーズ=「◯◯を1枚」、リール=素材の一言＋「（くわしい構成は投稿文のときに出ます）」の形（例:「◯◯の写真3枚と手元の動画1本（くわしい構成は投稿文のときに出ます）」）。★リールでも凝った動画編集はさせない（写真と10秒以内の動画をつなげるだけで作れる範囲）
- dest はフィード/リール/ストーリーズのどれか。リールは1〜2本まで（ハードルを上げない）

必ずこのJSONだけを返す:
{"items": [{"kata": "③", "kata_label": "学びになること", "dest": "リール",
  "hook": "1行目になる言葉", "shoot": "撮るもの1つ", "note": ""}, ...7つ、出す順番で]}
""",
    # ③-2 投稿文（フィード＋スレッズ）
    "post": HASSHIN_BASE_PROMPT + """
1つのネタから、そのまま貼れる投稿文を作ります。
★ネタの dest（フィード/リール/ストーリーズ）に合わせること:
- dest がリール → feed はリールのキャプションとして書く。1行目は悩みの言葉から（「動画を見てくれてありがとう」のような前置きは書かない）。さらに reel_plan（リールの構成案）を必ず出す
- dest がストーリーズ → feed は2〜3行の話しかける形。reel_plan は空の配列
- dest がフィード → 下のフィード版の形。reel_plan は空の配列

reel_plan（リールの構成案）のルール:
- カット3〜5個。「こういう写真や動画を撮って、この順でつなげる」が一目で分かるように
- 各カット = sozai（「写真」か「動画◯秒」）+ utsusu（映すもの。具体的に、撮りやすいもの）+ jimaku（画面に乗せる字幕1行）
- 動画は10秒以内の「スマホを置いて回すだけ」で撮れるものだけ。編集の腕がいるカットは出さない。写真だけの構成でもよい
- カット1の字幕は悩みの言葉（手が止まる1行）。最後のカットの字幕は行き先への一言
- ★字幕に読点「、」を使わない（テロップの字面が崩れるため。区切りたいときは文を分ける）
- 字幕は1行15文字以内くらい。短く

フィード版:
- 1行目=悩みの言葉から（ネタの hook をほぼそのまま）
- 本文=カルテの「解決できること」「きっかけと変化」から。ノウハウの羅列にしない
- 最後にご案内を1行だけ（例: 体験レッスンはプロフィールのリンクから↓）。押し売りしない
- 8〜12行くらい。絵文字は控えめ

スレッズ版:
- ★敬語のまま（タメ口にしない）。短く・本音寄りに（「〜からなんです」「〜なんですよね」）
- 3〜4行。写真なしでも出せる文にする
- ★強い断定・逆張り・煽りは禁止。「静かな本音」まで（反論ではなく「わかる」で返したくなる線。バズは狙わない）

必ずこのJSONだけを返す:
{"feed": "フィード投稿文（改行入り）", "threads": "スレッズ投稿文（改行入り）",
 "reel_plan": [{"sozai": "写真 または 動画◯秒", "utsusu": "映すもの", "jimaku": "字幕1行（読点なし）"}, ...リール以外は空の配列]}
""",
    # ③-2 直しボタン
    "post_fix": HASSHIN_BASE_PROMPT + """
投稿文の直しです。instruction に従って text を直します。
- 「もう少し短く」= 半分くらいに。1行目とご案内は残す
- 「ストーリーズ用にする」= 2〜3行。話しかける形に
- 「書き直す」= 同じネタ・同じカルテで別の切り口に
敬語のまま。煽らない。

必ずこのJSONだけを返す:
{"text": "直した文（改行入り）"}
""",
}


class HasshinKarteRequest(BaseModel):
    karte: dict


class HasshinAiRequest(BaseModel):
    mode: str
    data: dict


class HasshinWeekRequest(BaseModel):
    theme: str
    items: list


@app.get("/hasshin")
async def hasshin_page():
    return FileResponse("static/hasshin.html")


@app.get("/api/hasshin/state")
async def hasshin_state(authorization: str = Header(None)):
    member = await course_member_from_token(authorization)
    email = member["email"].strip().lower()
    karte = None
    week = None
    try:
        r = supabase.table("hasshin_karte").select("karte").eq("email", email).execute()
        if r.data:
            karte = r.data[0]["karte"]
        w = supabase.table("hasshin_weeks").select("theme, items, created_at").eq("email", email) \
            .order("created_at", desc=True).limit(1).execute()
        if w.data:
            week = w.data[0]
    except Exception as e:
        print(f"❌ 発信ツール読み込みエラー: {e}")
    return {"name": member["name"], "karte": karte, "week": week, "videos": HASSHIN_VIDEOS}


@app.post("/api/hasshin/karte")
async def hasshin_save_karte(request: HasshinKarteRequest, authorization: str = Header(None)):
    member = await course_member_from_token(authorization)
    try:
        supabase.table("hasshin_karte").upsert({
            "email": member["email"].strip().lower(),
            "karte": request.karte,
            "updated_at": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        print(f"❌ カルテ保存エラー: {e}")
        raise HTTPException(status_code=500, detail="保存できませんでした。少し待ってからもう一度お試しください")
    return {"status": "ok"}


@app.post("/api/hasshin/week")
async def hasshin_save_week(request: HasshinWeekRequest, authorization: str = Header(None)):
    member = await course_member_from_token(authorization)
    try:
        supabase.table("hasshin_weeks").insert({
            "email": member["email"].strip().lower(),
            "theme": request.theme,
            "items": request.items,
        }).execute()
    except Exception as e:
        print(f"❌ 週ネタ保存エラー: {e}")
    return {"status": "ok"}


@app.post("/api/hasshin/ai")
async def hasshin_ai(request: HasshinAiRequest, authorization: str = Header(None)):
    await course_member_from_token(authorization)
    prompt = HASSHIN_MODE_PROMPTS.get(request.mode)
    if not prompt:
        raise HTTPException(status_code=400, detail="不明なモードです")
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=2048,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(request.data, ensure_ascii=False)},
            ],
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"❌ 発信ツール生成エラー: {e}")
        raise HTTPException(status_code=500, detail="うまく作れませんでした。もう一度お試しください")


app.mount("/static", StaticFiles(directory="static"), name="static")
