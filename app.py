import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
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

def get_student_info(student_name: str) -> Optional[dict]:
    if STUDENTS_PATH.exists():
        data = json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))
        for s in data["students"]:
            if isinstance(s, dict) and s["name"] == student_name:
                return s
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

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/api/students")
async def get_students():
    if STUDENTS_PATH.exists():
        data = json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))
        students = data.get("students", [])
        names = [s["name"] if isinstance(s, dict) else s for s in students]
        names.sort(key=lambda n: 1 if "テスト" in n else 0)
        return {"students": names}
    return {"students": []}

@app.get("/api/status/{student_name}")
async def get_status(student_name: str):
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
async def chat(request: ChatRequest):
    if not request.student_name or not request.message:
        raise HTTPException(status_code=400, detail="名前とメッセージが必要です")

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

    system_message = SYSTEM_PROMPT + knowledge_base
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
async def get_progress(student_name: str):
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
async def update_progress(request: ProgressRequest):
    try:
        supabase.table("progress").upsert({
            "student_name": request.student_name,
            "completed": request.completed
        }).execute()
    except Exception as e:
        print(f"❌ 進捗保存エラー: {e}")
    return {"status": "ok"}

@app.get("/teacher")
async def teacher_page():
    return FileResponse("static/teacher.html")

@app.get("/api/summary/{student_name}")
async def get_summary(student_name: str):
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
async def get_conversation(student_name: str):
    history = load_conversation(student_name)
    return {"messages": history, "count": len(history)}

@app.post("/api/reset")
async def reset_conversation(request: ResetRequest):
    try:
        supabase.table("conversations").delete().eq("student_name", request.student_name).execute()
    except Exception as e:
        print(f"❌ リセットエラー: {e}")
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory="static"), name="static")
