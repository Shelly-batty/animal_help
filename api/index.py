import socket

socket.getfqdn = lambda host=None: 'localhost'  # 解决主机名编码问题
import os
from flask import Flask, render_template, request, redirect, url_for, flash,session,jsonify,send_from_directory
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime


# 让 pymysql 伪装成 MySQLdb，兼容旧代码
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.secret_key='12dedwf4f'

# 上传目录：和 api 同级，新建 uploads 文件夹
UPLOAD_FOLDER = r"C:\Users\sunyu\Desktop\流浪动物救助网站\uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# 允许的图片格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    # 检查文件名是否有扩展名，且扩展名在允许列表中
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# 数据库1连接配置
import os
import pymysql
from pymysql.cursors import DictCursor

def get_db1_connection():
    # 从环境变量读取数据库配置（Vercel 部署时设置）
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', '123456'),
        database=os.environ.get('DB_NAME', 'user_system'),
        charset='utf8mb4',
        port=int(os.environ.get('DB_PORT', 3307)),  # 端口需要转为整数
        cursorclass=DictCursor  # 以字典形式返回游标对象
    )
    return conn

#数据库2连接配置
def get_db2_connection():
    # 从环境变量读取数据库配置（Vercel 部署时设置）
    conn = pymysql.connect(
        host=os.environ.get('DB2_HOST', 'localhost'),
        user=os.environ.get('DB2_USER', 'root'),
        password=os.environ.get('DB2_PASSWORD', '123456'),
        database=os.environ.get('DB2_NAME', 'animal_system'),
        charset='utf8mb4',
        port=int(os.environ.get('DB2_PORT', 3307)),
        cursorclass=DictCursor  # 以字典形式返回数据
    )
    return conn


@app.route('/')
def root():
    if 'username' not in session:
        return render_template('pet.html')
    else:
        return render_template('welcome.html')

#首页
@app.route('/pet')
def home():
    return render_template('pet.html')

# ---------------------- 主页路由（连接数据库展示数据） ----------------------


@app.route('/register')
def index():
    conn = get_db1_connection()
    cursor = conn.cursor()
         # 查询所有用户数据
    cursor.execute('SELECT * FROM users;')
    users = cursor.fetchall()  # 获取所有数据
    cursor.close()
    conn.close()
    # 将数据传递给主页模板
    return render_template('register.html', users=users)

#待领养页面
@app.route('/待领养')
def adopt_wait():
    conn = get_db2_connection()
    cursor = conn.cursor()
     # 查询所有用户数据
    cursor.execute('SELECT * FROM animal_info WHERE is_adopted="未领养";')
    animal_info = cursor.fetchall()  # 获取所有数据
    cursor.close()
    conn.close()
    # 将数据传递给页面中
    return render_template('待领养.html',animals=animal_info)

#待领养页面
@app.route('/待领养', methods=['GET', 'POST'])
def adopt():
    if request.method == 'POST':
            name = request.form['name']
            data_type = request.form['animal_type']
            image_url=request.form['image_url']
            sex=request.form['sex']
            age=request.form['age']
            description=request.form['description']
            conn = get_db2_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM animal_info WHERE is_adopted = 0 ORDER BY create_time DESC;')
            user = cursor.fetchone()
            cursor.close()
            conn.close()
    return render_template('待领养.html')


@app.route('/animal/<int:animal_id>')
def animal_detail(animal_id):
    conn = get_db2_connection()
    # 用 dictionary=True 让返回结果是字典，方便模板用 .字段名 访问
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # 按 ID 查询单条动物数据
    cursor.execute('SELECT * FROM animal_info WHERE id = %s', (animal_id,))
    animal = cursor.fetchone()
    cursor.close()
    conn.close()
    # 把这只动物的数据传给详情模板
    return render_template('animal_detail.html', animal=animal)

@app.route('/领养申请表', methods=['GET', 'POST'])
def adopt_form():
    # 登录校验
    if 'username' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))

    username = session['username']

    # 获取用户信息
    conn_user = get_db1_connection()
    cur_user = conn_user.cursor(pymysql.cursors.DictCursor)
    cur_user.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_info = cur_user.fetchone()
    cur_user.close()
    conn_user.close()

    # 获取动物信息
    animal_id = request.args.get('animal_id', '')
    conn_animal = get_db2_connection()
    cur_animal = conn_animal.cursor(pymysql.cursors.DictCursor)
    cur_animal.execute("SELECT * FROM animal_info WHERE id = %s", (animal_id,))
    animal_info = cur_animal.fetchone()
    cur_animal.close()
    conn_animal.close()

    if request.method == 'POST':
        try:
            conn = get_db2_connection()
            cursor = conn.cursor()
            real_name = session.get('real_name', '')
            id_card = session.get('id_card', '')
            phone = session.get('phone', '')
            occupation = request.form.get('occupation', '')
            experience = request.form.get('experience', '')
            commitment = request.form.get('commitment', '')

            # 插入领养申请表（这里只存储了核心字段，如需其他字段请自行扩展）
            cursor.execute(
                '''INSERT INTO adoption
                   (animal_id, real_name, id_card, phone,occupation,experience,commitment)
                   VALUES (%s, %s, %s, %s,%s, %s, %s)''',
                (animal_id, real_name, id_card, phone,occupation,experience,commitment)
            )
            # 更新动物领养状态
            cursor.execute('UPDATE animal_info SET is_adopted = "已领养" WHERE id = %s', (animal_id,))
            conn.commit()
            cursor.close()
            conn.close()

            # 返回成功 JSON
            return jsonify({'status': 'success'})
        except Exception as e:
            # 数据库操作出错时回滚，并返回错误 JSON
            if conn:
                conn.rollback()
            return jsonify({'status': 'error', 'msg': '提交失败，请稍后重试'}), 500

    # GET 请求或 POST 失败后回退到渲染页面
    return render_template('领养申请表.html', users=user_info, animal=animal_info)


# 领养指南页面
@app.route('/领养指南')
def guide():
    return render_template('领养指南.html')
#喂养指南页面
@app.route('/喂养指南')
def food():
    return render_template('喂养指南.html')


# #求助
@app.route('/求助', methods=['GET', 'POST'])
def help():
    if request.method == 'POST':
        name = request.form.get('name', '')
        animal_type = request.form.get('animal_type', '')
        image_url = request.form.get('image_url', '')  # 缺失时默认是空字符串
        sex = request.form.get('sex', '')
        age = request.form.get('age', '')
        description = request.form.get('description', '')
        phone = request.form.get('phone', '')
        health = request.form.get('health', '')
        location = request.form.get('location','')
        image_url = ''
        if 'image_url' in request.files:
            file = request.files['image_url']
            if file and allowed_file(file.filename):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                safe_filename = secure_filename(file.filename)
                if not safe_filename:
                    safe_filename = "unknown.jpg"
                final_filename = f"{timestamp}_{safe_filename}"

                # 拼接完整保存路径
                save_path = os.path.join(UPLOAD_FOLDER, final_filename)
                print("实际保存路径：", save_path)  # 调试用，看路径对不对

                # 保存文件
                file.save(save_path)
                image_url = f"/uploads/{final_filename}"
                print("✅ 要存入数据库的 image_url：", image_url)

        try:
            conn = get_db2_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO animal_info
                   (animal_type,name,age, sex,health, description,location,phone, image_url)
                   VALUES (%s, %s, %s, %s, %s, %s,%s,%s,%s)''',
                (animal_type,name,age, sex,health, description,location,phone, image_url)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('adopt'))
        except Exception as e:
            conn.rollback()
    else:
        return render_template('求助.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        real_name=request.form.get('real_name', '')
        phone=request.form.get('phone', '')
        id_card=request.form.get('id_card', '')
        address=request.form.get('address', '')
    try:
        conn = get_db1_connection()
        cursor = conn.cursor()
        hashed_pw=generate_password_hash(password)
        sql = '''INSERT INTO users 
                 (username, password, real_name, phone, id_card, address)
                 VALUES (%s, %s, %s, %s, %s, %s)'''
        cursor.execute(sql, (username, hashed_pw, real_name, phone, id_card, address))
        conn.commit()

        flash('注册成功，请登录！')
        return redirect(url_for('login'))
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
        if conn:
            conn.rollback()
        flash(f'注册失败：{str(e)}')
        return render_template('register.html')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db1_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            flash('登录成功！')
            session['username'] = user['username']
            session['id_card']=user['id_card']
            session['phone']=user['phone']
            session['real_name']=user['real_name']
            return redirect(url_for('welcome'))
        else:
            flash('用户名或密码错误！')
    return render_template('login.html')

@app.route('/login_welcome')
def login_welcome():
    return render_template('login_welcome.html')

@app.route('/welcome')
def welcome():
    username=session.get('username')
    conn = get_db1_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_info = cursor.fetchone()  # 拿到单个用户数据
    cursor.close()
    conn.close()
    return render_template('welcome.html',user=user_info)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('已退出登录')
    return render_template('logout.html')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
