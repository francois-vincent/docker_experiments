A Postgresql image that persists data on a volume shared with host
==================================================================

TODO there should be unitary tests:
- build and run image, then create a base, a table and a record
- restart the container and check record in table
- remove container then run image again and chack record in table

these tests must be run via Fabric, so add an ssh server
if it is possible to change the Fabric connection backend, change it to docker exec !
