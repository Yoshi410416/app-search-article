from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

from models import init_db, get_db, get_cursor, get_delivery_time, set_delivery_time
from scheduler import start_scheduler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

with app.app_context():
    init_db()
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT * FROM admin')
    existing_admin = c.fetchone()
    if not existing_admin:
        default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        c.execute(
            'INSERT INTO admin (username, password_hash) VALUES (%s, %s)',
            ('admin', generate_password_hash(default_password))
        )
        conn.commit()
    conn.close()

start_scheduler()


@app.route('/')
def index():
    if 'admin' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        c = get_cursor(conn)
        c.execute('SELECT * FROM admin WHERE username = %s', (username,))
        admin = c.fetchone()
        conn.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin'] = username
            return redirect(url_for('dashboard'))
        flash('IDまたはパスワードが正しくありません')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT * FROM keywords ORDER BY id')
    keywords = c.fetchall()
    c.execute('SELECT * FROM recipients ORDER BY id')
    recipients = c.fetchall()
    conn.close()
    delivery_hour, delivery_minute = get_delivery_time()
    return render_template(
        'dashboard.html',
        keywords=keywords,
        recipients=recipients,
        delivery_hour=delivery_hour,
        delivery_minute=delivery_minute,
    )


@app.route('/keywords/add', methods=['POST'])
def add_keyword():
    if 'admin' not in session:
        return redirect(url_for('login'))
    keyword = request.form.get('keyword', '').strip()
    if keyword:
        conn = get_db()
        c = get_cursor(conn)
        try:
            c.execute('INSERT INTO keywords (keyword) VALUES (%s)', (keyword,))
            conn.commit()
            flash(f'キーワード「{keyword}」を追加しました', 'success')
        except Exception:
            conn.rollback()
            flash(f'キーワード「{keyword}」はすでに登録されています', 'danger')
        conn.close()
    return redirect(url_for('dashboard'))


@app.route('/keywords/delete/<int:id>', methods=['POST'])
def delete_keyword(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = get_cursor(conn)
    c.execute('DELETE FROM keywords WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    flash('キーワードを削除しました', 'success')
    return redirect(url_for('dashboard'))


@app.route('/recipients/add', methods=['POST'])
def add_recipient():
    if 'admin' not in session:
        return redirect(url_for('login'))
    email = request.form.get('email', '').strip()
    if email:
        conn = get_db()
        c = get_cursor(conn)
        try:
            c.execute('INSERT INTO recipients (email) VALUES (%s)', (email,))
            conn.commit()
            flash(f'メールアドレス「{email}」を追加しました', 'success')
        except Exception:
            conn.rollback()
            flash(f'メールアドレス「{email}」はすでに登録されています', 'danger')
        conn.close()
    return redirect(url_for('dashboard'))


@app.route('/recipients/delete/<int:id>', methods=['POST'])
def delete_recipient(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = get_cursor(conn)
    c.execute('DELETE FROM recipients WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    flash('メールアドレスを削除しました', 'success')
    return redirect(url_for('dashboard'))


@app.route('/settings/delivery-time', methods=['POST'])
def update_delivery_time():
    if 'admin' not in session:
        return redirect(url_for('login'))
    try:
        hour = int(request.form.get('hour', 8))
        minute = int(request.form.get('minute', 0))
    except ValueError:
        flash('無効な時間が入力されました', 'danger')
        return redirect(url_for('dashboard'))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        flash('時間は0〜23、分は0〜59の範囲で入力してください', 'danger')
        return redirect(url_for('dashboard'))
    set_delivery_time(hour, minute)
    from scheduler import reschedule
    reschedule(hour, minute)
    flash(f'配信時間を {hour:02d}:{minute:02d} に変更しました', 'success')
    return redirect(url_for('dashboard'))


@app.route('/send-test', methods=['POST'])
def send_test():
    if 'admin' not in session:
        return redirect(url_for('login'))
    from scheduler import run_daily_job
    try:
        run_daily_job()
        flash('テストメールを送信しました', 'success')
    except Exception as e:
        flash(f'送信エラー：{e}', 'danger')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
