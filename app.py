import os
import json
from functools import wraps

import bcrypt
import psycopg2
import psycopg2.errors
from flask import (
    Flask, g, session, request, redirect, url_for,
    render_template, flash, jsonify, send_from_directory
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'beyblade-x-secret-dev-key-change-in-prod')

APP_DIR = os.path.dirname(os.path.abspath(__file__))

WIN_POINTS = {
    'Spin/Stamina Finish': 1,
    'Over Finish': 2,
    'Burst Finish': 2,
    'Extreme Finish': 3,
}

# ---------------------------------------------------------------------------
# Parts DB
# ---------------------------------------------------------------------------
PARTS_DB = {}

def load_parts():
    global PARTS_DB
    parts_path = os.path.join(APP_DIR, 'parts_db.json')
    try:
        with open(parts_path, 'r', encoding='utf-8') as f:
            PARTS_DB = json.load(f)
    except FileNotFoundError:
        PARTS_DB = {'blades': [], 'ratchets': [], 'bits': []}

load_parts()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def _build_db_url():
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if 'sslmode=' not in url:
        url += ('&' if '?' in url else '?') + 'sslmode=require'
    return url

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(_build_db_url())
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    database_url = _build_db_url()
    if not database_url:
        return
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS beyblades (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                name TEXT,
                blade TEXT,
                ratchet TEXT,
                bit TEXT,
                UNIQUE(user_id, name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                bey1_id INT REFERENCES beyblades(id),
                bey2_id INT REFERENCES beyblades(id),
                winner_id INT REFERENCES beyblades(id),
                win_type TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'init_db error: {e}')


init_db()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# Routes: Auth
# ---------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, username, password_hash FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session.clear()
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('combos'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                (username, pw_hash)
            )
            conn.commit()
            cur.close()
            flash('Account created! Please log in.', 'info')
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Username already taken.', 'error')
    return render_template('register.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# Routes: Main
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('combos'))
    return redirect(url_for('login'))


@app.route('/combos')
@login_required
def combos():
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, name, blade, ratchet, bit FROM beyblades WHERE user_id = %s ORDER BY name',
        (user_id,)
    )
    rows = cur.fetchall()
    combos_list = []
    for row in rows:
        bey_id, name, blade, ratchet, bit = row
        # wins: battles where this bey was the winner
        cur.execute(
            """SELECT win_type FROM battles
               WHERE user_id = %s AND winner_id = %s""",
            (user_id, bey_id)
        )
        win_rows = cur.fetchall()
        wins = len(win_rows)
        pts = sum(WIN_POINTS.get(r[0], 0) for r in win_rows)
        # total battles involving this bey
        cur.execute(
            """SELECT COUNT(*) FROM battles
               WHERE user_id = %s AND (bey1_id = %s OR bey2_id = %s)""",
            (user_id, bey_id, bey_id)
        )
        total = cur.fetchone()[0]
        losses = total - wins
        win_pct = round((wins / total * 100) if total > 0 else 0, 1)
        combos_list.append({
            'id': bey_id,
            'name': name,
            'blade': blade,
            'ratchet': ratchet,
            'bit': bit,
            'wins': wins,
            'losses': losses,
            'battles': total,
            'win_pct': win_pct,
            'pts': pts,
        })
    cur.close()
    blade_names = [b['name'] for b in PARTS_DB.get('blades', [])]
    ratchet_names = [r['name'] for r in PARTS_DB.get('ratchets', [])]
    bit_names = [b['name'] for b in PARTS_DB.get('bits', [])]
    return render_template(
        'combos.html',
        combos=combos_list,
        blade_names=blade_names,
        ratchet_names=ratchet_names,
        bit_names=bit_names,
    )


@app.route('/combos/add', methods=['POST'])
@login_required
def combos_add():
    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    blade = request.form.get('blade', '').strip()
    ratchet = request.form.get('ratchet', '').strip()
    bit = request.form.get('bit', '').strip()
    if not name:
        flash('Combo name is required.', 'error')
        return redirect(url_for('combos'))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO beyblades (user_id, name, blade, ratchet, bit) VALUES (%s, %s, %s, %s, %s)',
            (user_id, name, blade, ratchet, bit)
        )
        conn.commit()
        cur.close()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash(f'A combo named "{name}" already exists.', 'error')
    return redirect(url_for('combos'))


@app.route('/combos/<int:bey_id>/delete', methods=['POST'])
@login_required
def combos_delete(bey_id):
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    # Verify ownership
    cur.execute('SELECT id FROM beyblades WHERE id = %s AND user_id = %s', (bey_id, user_id))
    if not cur.fetchone():
        flash('Combo not found.', 'error')
        cur.close()
        return redirect(url_for('combos'))
    cur.execute(
        'DELETE FROM battles WHERE user_id = %s AND (bey1_id = %s OR bey2_id = %s)',
        (user_id, bey_id, bey_id)
    )
    cur.execute('DELETE FROM beyblades WHERE id = %s AND user_id = %s', (bey_id, user_id))
    conn.commit()
    cur.close()
    flash('Combo deleted.', 'info')
    return redirect(url_for('combos'))


@app.route('/battle')
@login_required
def battle():
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, name FROM beyblades WHERE user_id = %s ORDER BY name',
        (user_id,)
    )
    combos_list = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
    cur.execute(
        """SELECT b.id, b.created_at,
                  bey1.name, bey2.name, winner.name, b.win_type
           FROM battles b
           JOIN beyblades bey1 ON b.bey1_id = bey1.id
           JOIN beyblades bey2 ON b.bey2_id = bey2.id
           JOIN beyblades winner ON b.winner_id = winner.id
           WHERE b.user_id = %s
           ORDER BY b.created_at DESC
           LIMIT 20""",
        (user_id,)
    )
    recent = []
    for r in cur.fetchall():
        recent.append({
            'id': r[0],
            'date': r[1].strftime('%Y-%m-%d %H:%M') if r[1] else '',
            'bey1': r[2],
            'bey2': r[3],
            'winner': r[4],
            'win_type': r[5],
            'pts': WIN_POINTS.get(r[5], 0),
        })
    cur.close()
    return render_template('battle.html', combos=combos_list, recent=recent, win_points=WIN_POINTS)


@app.route('/battle/record', methods=['POST'])
@login_required
def battle_record():
    user_id = session['user_id']
    bey1_id = request.form.get('bey1_id', type=int)
    bey2_id = request.form.get('bey2_id', type=int)
    winner_id = request.form.get('winner_id', type=int)
    win_type = request.form.get('win_type', '').strip()
    if not all([bey1_id, bey2_id, winner_id, win_type]):
        flash('All fields are required.', 'error')
        return redirect(url_for('battle'))
    if bey1_id == bey2_id:
        flash('Bey 1 and Bey 2 must be different combos.', 'error')
        return redirect(url_for('battle'))
    if winner_id not in (bey1_id, bey2_id):
        flash('Winner must be one of the two combos.', 'error')
        return redirect(url_for('battle'))
    if win_type not in WIN_POINTS:
        flash('Invalid win type.', 'error')
        return redirect(url_for('battle'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO battles (user_id, bey1_id, bey2_id, winner_id, win_type)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, bey1_id, bey2_id, winner_id, win_type)
    )
    conn.commit()
    cur.close()
    return redirect(url_for('battle'))


@app.route('/stats')
@login_required
def stats():
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT name FROM beyblades WHERE user_id = %s ORDER BY name',
        (user_id,)
    )
    combo_names = [r[0] for r in cur.fetchall()]
    cur.close()
    blade_names = [b['name'] for b in PARTS_DB.get('blades', [])]
    ratchet_names = [r['name'] for r in PARTS_DB.get('ratchets', [])]
    bit_names = [b['name'] for b in PARTS_DB.get('bits', [])]
    selected = request.args.get('combo', '')
    return render_template(
        'stats.html',
        combo_names=combo_names,
        blade_names=blade_names,
        ratchet_names=ratchet_names,
        bit_names=bit_names,
        selected_combo=selected,
    )


@app.route('/api/stats/<combo_name>')
@login_required
def api_stats(combo_name):
    user_id = session['user_id']
    part_type = request.args.get('part_type', 'any')
    part_name = request.args.get('part_name', '').strip()

    conn = get_db()
    cur = conn.cursor()

    # Get this combo
    cur.execute(
        'SELECT id, name, blade, ratchet, bit FROM beyblades WHERE user_id = %s AND name = %s',
        (user_id, combo_name)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'Combo not found'}), 404

    bey_id, name, blade, ratchet, bit = row

    # Build base query for all battles involving this combo
    # We need battles where bey1 or bey2 is our combo
    base_query = """
        SELECT b.id, b.created_at, b.winner_id, b.win_type,
               bey1.id as b1id, bey1.name as b1name, bey1.blade as b1blade, bey1.ratchet as b1ratchet, bey1.bit as b1bit,
               bey2.id as b2id, bey2.name as b2name, bey2.blade as b2blade, bey2.ratchet as b2ratchet, bey2.bit as b2bit
        FROM battles b
        JOIN beyblades bey1 ON b.bey1_id = bey1.id
        JOIN beyblades bey2 ON b.bey2_id = bey2.id
        WHERE b.user_id = %s AND (bey1.id = %s OR bey2.id = %s)
        ORDER BY b.created_at DESC
    """
    cur.execute(base_query, (user_id, bey_id, bey_id))
    all_battles = cur.fetchall()
    cur.close()

    # Filter by opponent part if requested
    def get_opp(battle_row):
        b1id = battle_row[4]
        if b1id == bey_id:
            return {'id': battle_row[9], 'name': battle_row[10], 'blade': battle_row[11],
                    'ratchet': battle_row[12], 'bit': battle_row[13]}
        else:
            return {'id': battle_row[4], 'name': battle_row[5], 'blade': battle_row[6],
                    'ratchet': battle_row[7], 'bit': battle_row[8]}

    filtered = []
    for br in all_battles:
        if part_type != 'any' and part_name:
            opp = get_opp(br)
            if part_type == 'blade' and opp['blade'] != part_name:
                continue
            if part_type == 'ratchet' and opp['ratchet'] != part_name:
                continue
            if part_type == 'bit' and opp['bit'] != part_name:
                continue
        filtered.append(br)

    wins = 0
    losses = 0
    pts = 0
    wt_counts = {wt: 0 for wt in WIN_POINTS}
    opponents = {}
    history = []

    for br in filtered:
        battle_id, created_at, winner_id, win_type = br[0], br[1], br[2], br[3]
        opp = get_opp(br)
        is_win = (winner_id == bey_id)
        battle_pts = WIN_POINTS.get(win_type, 0) if is_win else 0

        if is_win:
            wins += 1
            pts += WIN_POINTS.get(win_type, 0)
            if win_type in wt_counts:
                wt_counts[win_type] += 1
        else:
            losses += 1

        opp_name = opp['name']
        if opp_name not in opponents:
            opponents[opp_name] = {'name': opp_name, 'w': 0, 'l': 0, 'battles': 0, 'pts': 0}
        opponents[opp_name]['battles'] += 1
        if is_win:
            opponents[opp_name]['w'] += 1
            opponents[opp_name]['pts'] += WIN_POINTS.get(win_type, 0)
        else:
            opponents[opp_name]['l'] += 1

        history.append({
            'date': created_at.strftime('%Y-%m-%d') if created_at else '',
            'opp': opp_name,
            'result': 'WIN' if is_win else 'LOSS',
            'win_type': win_type,
            'pts': battle_pts,
        })

    total = wins + losses
    win_pct = round((wins / total * 100) if total > 0 else 0, 1)
    avg_pts = round(pts / total if total > 0 else 0, 2)

    opp_list = []
    for opp_name, od in opponents.items():
        t = od['battles']
        od['win_pct'] = round((od['w'] / t * 100) if t > 0 else 0, 1)
        opp_list.append(od)
    opp_list.sort(key=lambda x: x['battles'], reverse=True)

    return jsonify({
        'name': name,
        'blade': blade,
        'ratchet': ratchet,
        'bit': bit,
        'wins': wins,
        'losses': losses,
        'battles': total,
        'pts': pts,
        'win_pct': win_pct,
        'avg_pts_per_round': avg_pts,
        'wt_counts': wt_counts,
        'opponents': opp_list,
        'history': history,
    })


@app.route('/parts')
@login_required
def parts():
    return render_template('parts.html', parts_db=PARTS_DB)


@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(APP_DIR, 'images/' + filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
