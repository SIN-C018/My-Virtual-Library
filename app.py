
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from flask import session, flash, redirect, url_for, request
  # needed for session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


if os.path.exists('library.db'):
    os.chmod('library.db', 0o777)

db = SQLAlchemy(app)

# models are define here

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True)
    copies_available = db.Column(db.Integer, default=1)
    

class Borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_title = db.Column(db.String(200), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    erp_id = db.Column(db.String(20), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    return_date = db.Column(db.DateTime, nullable=True)

    @property
    def is_overdue(self):
        return datetime.utcnow() > self.due_date and self.return_date is None



# all seven routes are start from here

          
@app.before_request
def require_login():
    if request.endpoint not in ('login', 'static') and not session.get('logged_in'):
        return redirect(url_for('login'))
    
@app.route('/')
def index():
    search = request.args.get('search', '')
    query = Book.query
    if search:
        query = query.filter(Book.title.contains(search) | Book.author.contains(search))
    books = query.all()

    return render_template('index.html', books=books, search=search)

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        book = Book(
            title=request.form['title'],
            author=request.form['author'],
            # isbn=request.form['isbn'],
            # copies_available=int(request.form['copies'])
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added to catalog!', 'success')
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/add_borrow', methods=['GET', 'POST'])
def add_borrow():
    if request.method == 'POST':
        book_title = request.form['book_title'].strip()
        student_name = request.form['name'].strip()
        erp_id = request.form['erp_id'].strip()
        borrow_date_str = request.form.get('borrow_date', '')

        if not all([book_title, student_name, erp_id]):
            flash('All fields required!', 'danger')
            return redirect(url_for('add_borrow'))

        borrow_date = datetime.utcnow().date()
        if borrow_date_str:
            try:
                borrow_date = datetime.strptime(borrow_date_str, '%Y-%m-%d').date()
            except:
                pass

        borrow = Borrow(
            book_title=book_title,
            student_name=student_name,
            erp_id=erp_id,
            borrow_date=datetime.combine(borrow_date, datetime.min.time()),
            due_date=datetime.combine(borrow_date, datetime.min.time()) + timedelta(days=14)
        )
        db.session.add(borrow)
        db.session.commit()
        flash(f'Book issued: "{book_title}" to {student_name}', 'success')
        return redirect(url_for('index'))

    return render_template('add_borrow.html')

# DELETE BOOK FROM HOMEPAGE
@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted from catalog!', 'danger')
    return redirect(url_for('index'))

# delete borrow
@app.route('/delete_record/<int:borrow_id>')
def delete_record(borrow_id):
    borrow = Borrow.query.get_or_404(borrow_id)
    db.session.delete(borrow)
    db.session.commit()
    flash(f'Record deleted: "{borrow.book_title}" – {borrow.student_name}', 'danger')
    return redirect(url_for('history'))


@app.route('/return/<int:borrow_id>')
def return_book(borrow_id):
    borrow = Borrow.query.get_or_404(borrow_id)
    if not borrow.return_date:
        borrow.return_date = datetime.utcnow()
        db.session.commit()
        flash(f'Book returned: "{borrow.book_title}" by {borrow.student_name}', 'success')
    return redirect(url_for('history')) 

@app.route('/history')
def history():
    q = request.args.get('q', '').strip()
    borrows = Borrow.query.order_by(Borrow.borrow_date.desc())
    if q:
        borrows = borrows.filter(
            Borrow.book_title.ilike(f'%{q}%') |
            Borrow.student_name.ilike(f'%{q}%') |
            Borrow.erp_id.ilike(f'%{q}%')
        )
    borrows = borrows.all()
    return render_template('history.html', borrows=borrows)

@app.route('/edit_borrow/<int:borrow_id>', methods=['GET', 'POST'])
def edit_borrow(borrow_id):
    borrow = Borrow.query.get_or_404(borrow_id)
    if request.method == 'POST':
        if request.form.get('return_date'):
            borrow.return_date = datetime.strptime(request.form['return_date'], '%Y-%m-%d')
        db.session.commit()
        flash('Updated!', 'success')
        return redirect(url_for('history'))
    return render_template('edit_borrow.html', borrow=borrow)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Book.query.count() == 0:
            sample = Book(title="Higher Engineering Mths", author="BS Grewal")
            db.session.add(sample)
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=8000)