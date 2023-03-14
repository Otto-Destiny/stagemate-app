#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
from flask import jsonify
import logging
from logging import Formatter, FileHandler
from datetime import datetime
import sys
import traceback

import babel
import dateutil.parser
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_wtf import Form
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
#from sqlalchemy.orm import mapper

from forms import *


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://stevejohn:19370@localhost:5432/stagemate2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    seeking_talent = db.Column(db.String(120))
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('ShowClass', backref='venue', lazy=True)
    #artists = db.relationship('Artist', secondary='shows', backref=db.backref('venues', lazy=True))


    
class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.String(120))
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('ShowClass', backref='artist', lazy=True)

class ShowClass(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)
# and properties, as a database migration.


#db.registry.map_imperatively(ShowClass, db.Model.metadata.tables['shows'])
#mapper(ShowClass, Shows)

with app.app_context():
    db.create_all()
#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    # Get the venues and upcoming show counts
    venues = db.session.query(
        Venue.city,
        Venue.state,
        Venue.id,
        Venue.name,
        func.count(ShowClass.id).filter(ShowClass.start_time > datetime.now())
    ).outerjoin(ShowClass).group_by(Venue.id, Venue.city, Venue.state).all()

    # Group the venues by city and state
    grouped_venues = {}
    for venue in venues:
        city_state = (venue.city, venue.state)
        if city_state not in grouped_venues:
            grouped_venues[city_state] = {
                "city": venue.city,
                "state": venue.state,
                "venues": []
            }
        grouped_venues[city_state]["venues"].append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": venue[4] or 0
        })

    # Convert the dictionary to a list
    venue_data = [grouped_venues[k] for k in grouped_venues]

    return render_template('pages/venues.html', areas=venue_data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
 
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  with app.app_context():
    search_term=request.form.get('search_term', '')
    results = [venue for venue in Venue.query.filter(func.lower(Venue.name).contains(search_term.lower()))]
    response={
      "count": len(results),
      "data": [{
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": len([show for show in db.session.query(ShowClass).filter_by(venue_id=venue.id).all() 
                                  if ShowClass.start_time is not None and ShowClass.start_time > datetime.now()])
      } for venue in results]
    }
    db.session.close()
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  
  
  with app.app_context():
    venue = Venue.query.get(venue_id)
    upcoming_shows = list(db.session.query(ShowClass).join(Artist).filter(
      ShowClass.venue_id == venue_id,
      ShowClass.start_time > datetime.now()
      ).all())
    
    past_shows = list(db.session.query(ShowClass).join(Artist).filter(
    ShowClass.venue_id == venue_id,
    ShowClass.start_time < datetime.now()
    ).all())
    
    data= {
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website_link": venue.website_link,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link,
      
      "past_shows": [{
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': str(show.start_time)
    } 
                     for show in past_shows if show.artist.id is not None],
      "upcoming_shows": [{
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': str(show.start_time)
    } 
                         for show in upcoming_shows if show.artist.id is not None],  
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
    }
    
      
    #data = [d for d in venue_data if d['id'] == venue_id][0]
    #data = list(filter(lambda d: d['id'] == venue_id, [venue_data]))[0]
    return render_template('pages/show_venue.html', venue=data)
  


  #data = list(filter(lambda d: d['id'] == venue_id, [data1, data2, data3]))[0]
  #return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  with app.app_context():
    error = False
    body = {}
    try:
    # Create a new Venue object and add it to the session
      print(request.form)
      new_venue = Venue(
        name=request.form['name'],
        city=request.form['city'],
        state=request.form['state'],
        address=request.form['address'],
        phone=request.form['phone'],
        image_link=request.form['image_link'],
        facebook_link=request.form['facebook_link'],
        website_link=request.form['website_link'],
        genres=request.form['genres'],
        seeking_talent= request.form.get('seeking_talent'),
        seeking_description=request.form['seeking_description']
        )
      db.session.add(new_venue)
      db.session.commit()
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
      error == True
      traceback.print_exc()
        # Flash an error message and rollback the session if an exception occurs
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
      db.session.rollback()
      print(sys.exc_info())
    finally:
      # Close the session
      db.session.close()
    if error:
        # If there was an error, redirect to the form page with the error message
      return render_template('forms/new_venue.html', form=form)
    # TODO: on unsuccessful db insert, flash an error instead.
    else:
      return redirect(url_for('index'))

    #return render_template('pages/home.html')
#'''

@app.route('/venues/<venue_id>', methods=['POST','DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    with app.app_context():
      try:
          venue = Venue.query.filter_by(id=venue_id).first()
          if not venue:
            return jsonify({'error': 'Venue not found'}), 404
          Venue.query.filter_by(id=venue_id).delete()
          db.session.commit()
          #return jsonify({'success': True, 'message': 'Venue deleted successfully'}), 200
          flash('Venue deleted successfully', 'success')
          return redirect(url_for('venues'))
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({'error': 'Cannot delete the venue as it has upcoming shows.'}), 400
      except Exception as e:
          db.session.rollback()
          traceback.print_exc()
          flash('An error occurred while deleting the venue.', 'success')
          #return jsonify({'error': 'An error occurred while deleting the venue.'}), 500
      finally:
          db.session.close()
      return redirect(url_for('venues', venue_id=venue_id))

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

# -------------------------------------------------------------------
#  Artists
# -------------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database
  artist = Artist.query.all()
  data = [{
    "id": artists.id,
    "name": artists.name,
  } 
          for artists in artist]
  '''
  data=[{
    "id": 4,
    "name": "Guns N Petals",
  }, {
    "id": 5,
    "name": "Matt Quevedo",
  }, {
    "id": 6,
    "name": "The Wild Sax Band",
  }]
  '''
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  '''
  response={
    "count": 1,
    "data": [{
      "id": 4,
      "name": "Guns N Petals",
      "num_upcoming_shows": 0,
    }]
  }'''
  with app.app_context():
    search_term=request.form.get('search_term', '')
    results = [artist for artist in Artist.query.filter(func.lower(Artist.name).contains(search_term.lower()))]
    response={
      "count": len(results),
      "data": [{
        "id": artist.id,
        "name": artist.name,
        "num_upcoming_shows": len([show for show in db.session.query(ShowClass).filter_by(artist_id=artist.id).all() 
                                  if ShowClass.start_time is not None and ShowClass.start_time > datetime.now()])
      } for artist in results]
    }
    db.session.close()
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id
    with app.app_context():
      artist = Artist.query.get(artist_id)
      
      upcoming_shows = list(db.session.query(ShowClass).join(Artist).filter(
      ShowClass.artist_id == artist_id,
      ShowClass.start_time > datetime.now()
      ).all())
      
      past_shows = list(db.session.query(ShowClass).join(Artist).filter(
      ShowClass.artist_id == artist_id,
      ShowClass.start_time < datetime.now()
      ).all())
    
      data= {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website_link": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,       
        "past_shows": [{
          'artist_id': show.artist.id,
          'artist_name': show.artist.name,
          'artist_image_link': show.artist.image_link,
          'start_time': str(show.start_time)
          } for show in past_shows],
        "upcoming_shows": [{
          'artist_id': show.artist.id,
          'artist_name': show.artist.name,
          'artist_image_link': show.artist.image_link,
          'start_time': str(show.start_time)
      } for show in upcoming_shows],  
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
      }
      
      return render_template('pages/show_artist.html', artist=data)
    #data = list(filter(lambda d: d['id'] == artist_id, [data1, data2, data3]))[0]
    #return render_template('pages/show_artist.html', artist=data)




#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  form = ArtistForm(obj=artist)
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
    with app.app_context():
      artist = Artist.query.get(artist_id)
      form = ArtistForm(request.form)
      print('form data:', request.form)
        # Validate the form
      if not form.validate():
        print(form.errors)
        traceback.print_exc()
        print(sys.exc_info())
        flash('An error occurred. Artist ' + artist.name + ' could not be updated.')
        return redirect(url_for('edit_artist', artist_id=artist_id))
        
      # Update the venue with the new form data
      artist.name = form.name.data
      artist.genres = form.genres.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.website_link = form.website_link.data
      artist.facebook_link = form.facebook_link.data
      artist.seeking_venue = form.seeking_venue.data
      artist.seeking_description = form.seeking_description.data
      artist.image_link = form.image_link.data

      # Commit the changes to the database
      db.session.commit()
      # Redirect to the show_venue function with the updated venue_id parameter
      flash('Artist ' + artist.name + ' was successfully updated!')

      return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  venue_data={
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }
  form = VenueForm(obj=venue)
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
  with app.app_context():
    venue = Venue.query.get(venue_id)
    form = VenueForm(request.form)
    print('form data:', request.form)
      # Validate the form
    if not form.validate():
      print(form.errors)
      traceback.print_exc()
      print(sys.exc_info())
      flash('An error occurred. Venue ' + venue.name + ' could not be updated.')
      return redirect(url_for('edit_venue', venue_id=venue_id))
      
    # Update the venue with the new form data
    venue.name = form.name.data
    venue.genres = form.genres.data
    venue.address = form.address.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.phone = form.phone.data
    venue.website_link = form.website_link.data
    venue.facebook_link = form.facebook_link.data
    venue.seeking_talent = form.seeking_talent.data
    venue.seeking_description = form.seeking_description.data
    venue.image_link = form.image_link.data

    # Commit the changes to the database
    db.session.commit()
    
    # Redirect to the show_venue function with the updated venue_id parameter
    flash('Venue ' + venue.name + ' was successfully updated!')

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  with app.app_context():
    error = False
    try:
    # Create a new Venue object and add it to the session
      print(request.form)
      new_artist = Artist(
        name=request.form['name'],
        city=request.form['city'],
        state=request.form['state'],
        phone=request.form['phone'],
        image_link=request.form['image_link'],
        facebook_link=request.form['facebook_link'],
        website_link=request.form['website_link'],
        genres=request.form['genres'],
        seeking_venue= request.form.get('seeking_venue'),
        seeking_description=request.form['seeking_description']
        )
      db.session.add(new_artist)
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
      error == True
      traceback.print_exc()
        # Flash an error message and rollback the session if an exception occurs
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
      db.session.rollback()
      print(sys.exc_info())
    finally:
      # Close the session
      db.session.close()
    if error:
        # If there was an error, redirect to the form page with the error message
      return render_template('forms/new_artist.html', form=form)
  # on successful db insert, flash success
  #flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  with app.app_context():
    show = list(db.session.query(ShowClass).join(Artist).filter(
      ShowClass.start_time > datetime.now()
      ).all())
    data=[{
      "venue_id": shows.venue.id,
      "venue_name": shows.venue.name,
      "artist_id": shows.artist.id,
      "artist_name": shows.artist.name,
      "artist_image_link": shows.artist.image_link,
      "start_time": str(shows.start_time)
    } for shows in show]
    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  with app.app_context():
    error = False
    try:
    # Create a new Venue object and add it to the session
      print(request.form)
      new_show = ShowClass(
        artist_id=request.form['artist_id'],
        venue_id=request.form['venue_id'],
        start_time=request.form['start_time'],
        )
      db.session.add(new_show)
      db.session.commit()
      flash('Show ' + ' was successfully listed!')
    except:
      error == True
      traceback.print_exc()
        # Flash an error message and rollback the session if an exception occurs
      flash('An error occurred. Show ' + ' could not be listed.')
      db.session.rollback()
      print(sys.exc_info())
    finally:
      # Close the session
      db.session.close()
    if error:
        # If there was an error, redirect to the form page with the error message
      return render_template('forms/new_show.html', form=form)
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
