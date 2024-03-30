from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired
import requests
import os


API_READ_ACCESS_TOKEN = os.environ["API_READ_ACCESS_TOKEN"]
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_READ_ACCESS_TOKEN}"
}

app = Flask(__name__)
app.config['SECRET_KEY'] = "Your form's secret key to enable CSRF protection"
Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies-collection.db"
database = SQLAlchemy(model_class=Base)
database.init_app(app)


# CREATE TABLE
class Movie(database.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String, nullable=True)
    img_url: Mapped[str] = mapped_column(String, nullable=False)


with app.app_context():
    database.create_all()


# Create form:
class UpdateForm(FlaskForm):
    movie_id = HiddenField()
    rating = StringField(label="Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField(label="Your Review", validators=[DataRequired()])
    submit = SubmitField(label="Done")


class AddForm(FlaskForm):
    new_title = StringField(label="Movie Title", validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


@app.route("/")
def home():

    # Renders rankings of all saved movies (order_by orders from lowest rating to highest rating):
    ranked_movies = database.session.execute(database.select(Movie).order_by(Movie.rating)).scalars()
    movies_list = ranked_movies.all()[::-1]

    for num in range(len(movies_list)):
        movies_list[num].ranking = num+1
        database.session.commit()

    ranked_movies_updated = database.session.execute(database.select(Movie).order_by(Movie.rating)).scalars()
    return render_template("index.html", all_movies=ranked_movies_updated)


@app.route("/edit", methods=["GET", "POST"])
def edit_rating():

    # Before user submits the edit form:
    if request.method == "GET":

        # If user is redirected from select.html after clicking on the link in add.html:
        movie_api_id = request.args.get("movie_api_id")
        if movie_api_id is not None:
            url = f"https://api.themoviedb.org/3/movie/{movie_api_id}"
            response = requests.get(url=url, headers=headers)
            movie_data = response.json()
            new_movie = Movie(
                title=movie_data["title"],
                year=movie_data["release_date"].split("-")[0],
                description=movie_data["overview"],
                rating=None,
                ranking=None,
                review=None,
                img_url=f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
            )
            database.session.add(new_movie)
            database.session.commit()

            new_movie = database.session.execute(database.select(Movie).where(Movie.title
                                                                              == movie_data["title"])).scalar()
            movie_title = movie_data["title"]
            edit_form = UpdateForm(movie_id=new_movie.id)

        # If user pressed the update button to change ratings:
        # (id arg is passed from home page when clicking "update" button manually):
        else:
            movie_id = request.args["id"]
            movie_title = request.args["title"]
            edit_form = UpdateForm(movie_id=movie_id)

        return render_template("edit.html", form=edit_form, title=movie_title)

    # After user submits the form, movie rating is updated:
    else:
        movie_id = request.form["movie_id"]
        movie_to_update = database.get_or_404(Movie, movie_id)
        movie_to_update.rating = request.form["rating"]
        movie_to_update.review = request.form["review"]
        database.session.commit()
        return redirect(url_for('home'))


@app.route("/delete")
def delete_movie():
    movie_id = request.args["id"]
    movie_to_delete = database.get_or_404(Movie, movie_id)
    database.session.delete(movie_to_delete)
    database.session.commit()
    return redirect(url_for('home'))


@app.route("/add", methods=["GET", "POST"])
def add_movie():

    # Step 1: Renders form for user to enter name of movie they are searching for:
    if request.method == "GET":
        add_form = AddForm()
        return render_template("add.html", form=add_form)

    # Step 2: Then posts title of movie user is searching for, which is fed into an API:
    else:
        title = request.form["new_title"]

        parameters = {
            "query": title
        }

        response = requests.get(url="https://api.themoviedb.org/3/search/movie", params=parameters, headers=headers)
        movie_data = response.json()["results"]
        return render_template("select.html", movie_data=movie_data)


if __name__ == '__main__':
    app.run(debug=True)
