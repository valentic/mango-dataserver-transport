###########################################################################
#
#   Mango Data Models
#
#   Needs postgresql postgresql-server sqlalchemy
#
#   2021-08-01  Todd Valentic
#               Initial implementation.
#
#   2022-04-13  Todd Valentic
#               Add StationInstrument table 
#
#   2022-04-21	Todd Valentic
#		        Add QuicklookMovie table
#
###########################################################################

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey, func, Index
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from sqlalchemy import DateTime, String, BigInteger, Integer, Float, Boolean, Numeric
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects import postgresql

#database = 'postgresql://@/mango'
database = 'postgresql://transport@localhost:15432/mango'
session = scoped_session(sessionmaker())

Base = declarative_base()
Base.query = session.query_property()
Base.metadata.bind = create_engine(database)

#-- Utility functions --------------------------------------------

def create():
    Base.metadata.create_all()

def add(entry):
    session.add(entry)

def delete(entry):
    session.delete(entry)

def save(entry):
    session.add(entry)

def merge(entry):
    return session.merge(entry)

def commit():
    session.commit()

def rollback():
    session.rollback()

def remove():
    session.remove()

#------------------------------------------------------------------------------
# Stations
#------------------------------------------------------------------------------

class Station(Base):

    __tablename__ = 'station'

    id          = Column(Integer, primary_key=True)
    name        = Column(String, unique=True)
    label       = Column(String)
    model_id    = Column(Integer, ForeignKey('system_model.id'))
    status_id   = Column(Integer, ForeignKey('status.id'))

    def __repr__(self):
        return '<Station %s (%s)>' % \
            (self.name,self.id)

class Status(Base):

    __tablename__ = 'status'

    id      = Column(Integer, primary_key=True)
    name    = Column(String, unique=True)
    label   = Column(String)

    def __repr__(self):
        return '<Status %s (%s)>' % \
            (self.name,self.id)

class SystemModel(Base):

    __tablename__ = 'system_model'

    id      = Column(Integer, primary_key=True)
    name    = Column(String, unique=True)
    label   = Column(String)

    def __repr__(self):
        return '<SystemModel %s (%s)>' % \
            (self.name,self.id)

class Device(Base):

    __tablename__ = 'device'

    id      = Column(Integer, primary_key=True)
    name    = Column(String, unique=True)
    label   = Column(String)

    def __repr__(self):
        return '<Device %s (%s)>' % \
            (self.name,self.id)

class Instrument(Base):

    __tablename__ = 'instrument'

    id          = Column(Integer, primary_key=True)
    name        = Column(String, unique=True)
    label       = Column(String)

    def __repr__(self):
        return '<Instrument %s (%s)>' % \
            (self.name,self.id)

class StationInstrument(Base):

    __tablename__ = 'stationinstrument'

    id              = Column(Integer, primary_key=True)
    station_id      = Column(Integer, ForeignKey('station.id'))
    instrument_id   = Column(Integer, ForeignKey('instrument.id'))

    station = relationship('Station', backref='station')
    instrument = relationship('Instrument', backref='instrument')

    def __repr__(self):
        return '<StationInstrument %s (station %s, instrument %s)>' % \
            (self.id, self.station_id, self.instrument_id)

#------------------------------------------------------------------------------
# Images 
#------------------------------------------------------------------------------

class Image(Base):

    __tablename__ = 'image'


    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    device_id       = Column(Integer, ForeignKey('device.id'))
    serialnum       = Column(Integer)

    latitude        = Column(Float)
    longitude       = Column(Float)
    exposure_time   = Column(Float)
    ccd_temp        = Column(Float)
    set_point       = Column(Float)
    image_bytes     = Column(Integer)
    x               = Column(Integer)
    y               = Column(Integer)
    width           = Column(Integer)
    height          = Column(Integer)
    bin_x           = Column(Integer)
    bin_y           = Column(Integer)

    stationinstrument_id = Column(Integer, ForeignKey('stationinstrument.id'))

    __table_args__ = (
        Index('stationinstrument_id_timestamp_idx',stationinstrument_id,timestamp),
    )

    def __repr__(self):
        return '<Image %s %s>' % \
            (self.timestamp,self.stationinstrument_id)

class QuickLookMovie(Base):

    __tablename__ = 'quicklookmovie'

    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    stationinstrument_id = Column(Integer, ForeignKey('stationinstrument.id'))

    __table_args__ = (
        Index('quicklookmovie_stationinstrument_id_timestamp_idx',stationinstrument_id,timestamp),
    )

    def __repr__(self):
        return '<QuickLookMovie %s %s>' % \
            (self.timestamp,self.stationinstrument_id)

#------------------------------------------------------------------------------
# FPI Movies 
#------------------------------------------------------------------------------

class CombinedMovie(Base):
    
    __tablename__ = 'combinedmovie'

    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    instrument_id   = Column(Integer, ForeignKey('instrument.id'))
    src_filename    = Column(String)
    src_modtime     = Column(Integer)
    src_filesize    = Column(Integer)

    __table_args__ = (
        Index('combinedmovie_timestamp_idx',timestamp),
    )

    def __repr__(self):
        return '<CombinedMovie %s >' % self.timestamp

#------------------------------------------------------------------------------
# System 
#------------------------------------------------------------------------------

class Server(Base):

    __tablename__ = 'server'

    id          = Column(Integer, primary_key=True)
    station_id  = Column(Integer, ForeignKey('station.id'))
    model_id    = Column(Integer, ForeignKey('system_model.id'))
    host        = Column(String)
    label       = Column(String)

    def __repr__(self):
        return '<Server %s (%s)>' % (self.host,self.id)

    __table_args__ = (
        UniqueConstraint('station_id','host'),
        )

class ServerData(Base):

    __tablename__ = 'server_data'

    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    server_id       = Column(Integer,ForeignKey('server.id'))

    load_15min      = Column(Float)
    load_5min       = Column(Float)
    load_1min       = Column(Float)

    uptime          = Column(Float)

    swaptotal       = Column(BigInteger)
    swapfree        = Column(BigInteger)
    swapcached      = Column(BigInteger)
    slab            = Column(BigInteger)
    buffers         = Column(BigInteger)
    memfree         = Column(BigInteger)
    memtotal        = Column(BigInteger)
    cached          = Column(BigInteger)
    dirty           = Column(BigInteger)
    mapped          = Column(BigInteger)
    active          = Column(BigInteger)
    inactive        = Column(BigInteger)
    pagetables      = Column(BigInteger)
    anonpages       = Column(BigInteger)

    __table_args__ = (Index('server_data_server_id_timestamp_idx','server_id','timestamp'),)

class NetworkDevice(Base):

    __tablename__ = 'network_devices'

    id          = Column(Integer, primary_key=True)
    server_id   = Column(Integer,ForeignKey('server.id'))
    name        = Column(String)

    __table_args__ = (
        UniqueConstraint('server_id','name'),
        )

class NetworkData(Base):

    __tablename__ = 'network_data'

    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    device_id       = Column(Integer,ForeignKey('network_devices.id'))

    tx_errs         = Column(BigInteger)
    tx_drop         = Column(BigInteger)
    tx_bytes        = Column(BigInteger)
    tx_rate         = Column(Float)
    tx_packets      = Column(BigInteger)

    rx_errs         = Column(BigInteger)
    rx_drop         = Column(BigInteger)
    rx_bytes        = Column(BigInteger)
    rx_rate         = Column(Float)
    rx_packets      = Column(BigInteger)

    __table_args__ = (Index('network_data_device_id_timestamp_idx','device_id','timestamp'),)

class Filesystem(Base):

    __tablename__ = 'filesystems'

    id          = Column(Integer, primary_key=True)
    server_id   = Column(Integer,ForeignKey('server.id'))
    name        = Column(String)

    __table_args__ = (
        UniqueConstraint('server_id','name'),
        )

class FilesystemData(Base):

    __tablename__ = 'filesystem_data'

    id              = Column(Integer, primary_key=True)
    timestamp       = Column(DateTime(timezone=True))
    filesystem_id   = Column(Integer,ForeignKey('filesystems.id'))

    totalbytes      = Column(BigInteger)
    freebytes       = Column(BigInteger)
    usedbytes       = Column(BigInteger)
    usedpct         = Column(Float)

    __table_args__ = (Index('filesystem_data_filesystem_id_timestamp_idx','filesystem_id','timestamp'),)

