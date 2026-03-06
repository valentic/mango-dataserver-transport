-- Example call: 
-- psql -t -h localhost -p 15432 -U transport mango -f imagelist-wrapper.sql  -v station='blo' -v instrument='greenline' -v date='now'

SELECT * FROM imagelist(:'station',:'instrument',date :'date')
