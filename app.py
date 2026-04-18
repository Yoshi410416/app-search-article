from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

from models import init_db, get_db, get_cursor
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
            'INSERT INTO admin (username, password_hash) VALUES (?, ?)',
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
        c.execute('SELECT * FROM admin WHERE username = ?', (username,))
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
    return render_template('dashboard.html', keywords=keywords, recipients=recipients)


@app.route('/keywords/add', methods=['POST'])
def add_keyword():
    if 'admin' not in session:
        return redirect(url_for('login'))
    keyword = request.form.get('keyword', '').strip()
    if keyword:
        conn = get_db()
        c = get_cursor(conn)
        try:
            c.execute('INSERT INTO keywords (keyword) VALUES (?)', (keyword,))
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
    c.execute('DELETE FROM keywords WHERE id = ?', (id,))
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
            c.execute('INSERT INTO recipients (email) VALUES (?)', (email,))
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
    c.execute('DELETE FROM recipients WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('メールアドレスを削除しました', 'success')
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
