from flask import Flask, render_template, request,redirect, url_for, flash,session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime
import locale

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///../database/clientes.db'
app.config['SECRET_KEY'] = 'LUCASMORAES'
db = SQLAlchemy(app)

class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key =  True) #id do login do utilizador
    usuario = db.Column(db.String(12), unique = True) # Nome de usuário do utilizador, podendo ter até 12 dígitos
    password = db.Column(db.String(12)) # Password do ulitizador, podendo ter até 12 dígitos
    categoria = db.Column(db.String(10))

class Carro(db.Model):
    __tablename__ = "veiculoss"
    id = db.Column(db.Integer, primary_key =  True)
    modelo = db.Column(db.String(200))
    categoria = db.Column(db.String(10))
    diaria = db.Column(db.Integer)
    disponivel = db.Column(db.Boolean, default = True)
    data_disp = db.Column(db.DateTime, default=datetime.utcnow)


class Transacao(db.Model):
    __tablename__ = "transacoes"
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    cliente_ = db.Column(db.String, nullable=False)
    modelo_v = db.Column(db.String, nullable=False)
    data_rec = db.Column(db.Date, nullable=False)
    data_dev = db.Column(db.Date, nullable=False)
    preco_total = db.Column(db.Float, nullable=False)

def validar_login(usuario, password):

    connection = sqlite3.connect('database/clientes.db')
    cursor = connection.cursor()
    #Filtro de user e password
    query = "SELECT * FROM clientes WHERE usuario=? AND password=?"
    cursor.execute(query, (usuario, password))
    user = cursor.fetchone()
    connection.close()

    if user:
        return True
    else:
        return False

def validar_cartao(nome,cartao,validade,codigo):

    if len(cartao)==16 and len(validade)==7 and len(codigo)==3 and len(nome)>=6:
        return True
    else:
        return False


@app.route('/login' , methods = ['GET', 'POST'])
def pagina_principal():
    usuario = request.form.get('login-cliente')
    password = request.form.get('password-cliente')

    if validar_login(usuario,password) == True:
        connection = sqlite3.connect('database/clientes.db')
        cursor = connection.cursor()
        query = "SELECT usuario, categoria FROM clientes WHERE usuario=? AND password=?"
        cursor.execute(query, (usuario, password))
        user = cursor.fetchone()
        connection.close()
        username, categ = user
        session['categoria'] = categ
        session['usuario'] = username
        if categ == 'Gold':
            return render_template('catalogo_gold.html',usuario = usuario)
        if categ == 'Silver':
            return render_template('catalogo_silver.html',usuario = usuario)
        else:
            return render_template('catalogo_economic.html',usuario = usuario)

    else:
        flash('Credenciais de login incorretas.')
        return render_template('index.html')

@app.route('/total', methods=['GET','POST'])
def data_reserva():
    categ = session['categoria']
    data_recolha_date = request.form['data_recolha']
    data_devolucao_date = request.form['data_devolucao']
    session['data_recolha'] = data_recolha_date
    session['data_devolucao'] = data_devolucao_date
    connection = sqlite3.connect('database/clientes.db')
    cursor = connection.cursor()
    query = "SELECT DISTINCT modelo FROM veiculoss  WHERE  data_disp < ? AND categoria=?"
    cursor.execute(query,(data_recolha_date,categ))

    carros_disponiveis = [row[0] for row in cursor.fetchall()]
    connection.close()
    return render_template('escolha_viatura.html', data_recolha = data_recolha_date, data_devolucao = data_devolucao_date,carros_disponiveis=carros_disponiveis)

@app.route('/pagamento', methods=['GET','POST'])
def calcular_total():
    carro = request.form.get('carro')
    session['carro'] = carro
    connection = sqlite3.connect('database/clientes.db')
    cursor = connection.cursor()
    query = "SELECT modelo , diaria FROM veiculoss WHERE veiculoss.modelo = ?"
    cursor.execute(query, (carro,))
    carro_selec = cursor.fetchone()
    modelo, diaria_carro = carro_selec
    connection.close()
    data_recolha = session['data_recolha']
    data_devolucao = session['data_devolucao']
    data_recolha_date = datetime.strptime(data_recolha, "%Y-%m-%d")
    data_devolucao_date = datetime.strptime(data_devolucao, "%Y-%m-%d")

    total_diarias = (data_devolucao_date - data_recolha_date) * diaria_carro
    total_dias = total_diarias.days
    session['total'] = total_dias
    locale.setlocale(locale.LC_ALL, 'en_US.utf-8')
    total = locale.currency(total_dias, grouping=True)
    session['total_euros']=total
    return render_template('confirmacao.html',total = total, carro = carro,data_recolha = data_recolha, data_devolucao = data_devolucao)

@app.route('/finalizacao' , methods=['GET','POST'])
def finaliza_reserva():
    carro = session['carro']
    data_r = datetime.strptime(session['data_recolha'], '%Y-%m-%d').date()
    data_d = datetime.strptime(session['data_devolucao'], '%Y-%m-%d').date()
    user = session['usuario']
    total = session['total']
    opcao_pagamento = request.form.get('opcao-pagamento')
    nome = request.form.get('nome')
    cartao = request.form['numero-cartao']
    validade = request.form.get('validade')
    codigo = request.form.get('codigo-seguranca')
    iban = request.form.get('numero-iban')
    reserva = Transacao(cliente_=user,modelo_v=carro,data_rec=data_r,data_dev=data_d,preco_total=total)
    with app.app_context():
        db.session.add(reserva)
        db.session.commit()

    if opcao_pagamento == 'cartao':
        if validar_cartao(nome,cartao,validade,codigo) == True:
            connection = sqlite3.connect('database/clientes.db')
            cursor = connection.cursor()
            cursor.execute("UPDATE veiculoss SET data_disp = ? WHERE modelo = ?", (data_d, carro))
            connection.commit()
            connection.close()
            reserva = Transacao(cliente_=user, modelo_v=carro, data_rec=data_r, data_dev=data_d, preco_total=total)
            with app.app_context():
                db.session.add(reserva)
                db.session.commit()
            return render_template('pagina_final.html', user=user, carro=carro,data_recolha = session['data_recolha'], data_devolucao = session['data_devolucao'])
        else:
            flash('Dados do cartão são inválidos.')
            return render_template('confirmacao.html',total = session['total_euros'], carro = carro,data_recolha =session['data_recolha'], data_devolucao = session['data_devolucao'])
    if opcao_pagamento == 'transferencia':
        if len(iban) == 29:
            connection = sqlite3.connect('database/clientes.db')     #FALTA COLOCAR UM IBAN COMO HIDDEN NA OPÇÃO DE TRANFER
            cursor = connection.cursor()
            cursor.execute("UPDATE veiculoss SET data_disp = ? WHERE modelo = ?", (data_d, carro))
            connection.commit()
            connection.close()
            reserva = Transacao(cliente_=user, modelo_v=carro, data_rec=data_r, data_dev=data_d, preco_total=total)
            with app.app_context():
                db.session.add(reserva)
                db.session.commit()
            return render_template('pagina_final.html', user=user, carro=carro, data_recolha=session['data_recolha'],data_devolucao=session['data_devolucao'])
        else:
            flash('Informe um IBAN válido.')
            return render_template('confirmacao.html', total=session['total_euros'], carro=carro,data_recolha=session['data_recolha'], data_devolucao=session['data_devolucao'])
    else:
        flash('Selecione uma opção de pagamento.')
        return render_template('confirmacao.html',total = session['total_euros'], carro = carro,data_recolha = session['data_recolha'], data_devolucao = session['data_devolucao'])

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')



with app.app_context():
    db.create_all()
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)

