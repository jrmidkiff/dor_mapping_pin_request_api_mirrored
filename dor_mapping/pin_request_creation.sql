-- Sequence and Table Creation
drop sequence if exists pin_request_seq;
CREATE SEQUENCE pin_request_seq 
	AS integer;
select setval('pin_request_seq',  (SELECT MAX(pin) FROM parcel_rev_evw pre));

CREATE TABLE dor.pin_requests (
	pin_assigned int4 NOT NULL,
	requester_named_version text NULL,
	addr_std text NULL,
	mapreg text NULL,
	parcel_type text NULL,
	parcel_objectid int4 NULL,
	request_date timestamptz NULL,
	CONSTRAINT pin_request_test_pkey PRIMARY KEY (pin_assigned)
);
commit;
select * 
from parcel_rev_evw pre 
where objectid in (781040, 781041);

-- 
SELECT sde.sde_set_current_version('dor');
SELECT sde.sde_edit_version('dor', 1);
commit;
SELECT sde.sde_edit_version('dor', 2);


select pin, addr_std , mapreg , * 
from parcel_rev_evw pre 
where status in (1,3) and pin is null
order by objectid;

SELECT sde.sde_edit_version('dor', 2);

--
SELECT sde.sde_set_current_version('james_midkiff');
SELECT sde.sde_edit_version('james_midkiff', 1);

select pin, addr_std , mapreg, status , *
from parcel_rev_evw pre 
where status in (1,3)
order by pin desc nulls last;

--select pin, addr_std , mapreg , status , * 
--from parcel_rev_evw pre 
--where status in (1,3) and pin is null
--order by objectid;

SELECT sde.sde_edit_version('james_midkiff', 2);

-- 
SELECT sde.sde_set_current_version('james_midkiff');
SELECT sde.sde_edit_version('james_midkiff', 1);

-- 1 - Get objectids
SELECT objectid FROM parcel_rev_evw WHERE status IN (1,3) AND addr_std = '1817 RANSTEAD ST' AND mapreg = '001S110291'; -- AND pin IS null;

-- 2 - Update parcel_rev_evw pin
UPDATE parcel_rev_evw SET pin = NULL
-- pin = nextval('pin_request_seq') 
WHERE objectid = ANY(array[777451]);

-- 3.1 - Get new pins
SELECT pin FROM parcel_rev_evw WHERE status IN (1,3) AND objectid = ANY(array[777451]);
-- 3.2 - Check for duplicates
--select * 
--from (
--	select pin , count(*) as count
--	from parcel_rev_evw pre 
--    where status in (1,3)
--	group by pin 
--	having pin is not null 
--	order by pin
--    ) as counts
--where pin = ANY(array[777451]) and counts.count > 1

-- 4 - Insert into PIN requests
--INSERT INTO pin_requests (pin_assigned, requester_named_version, addr_std, mapreg, parcel_type, parcel_objectid, request_date)
--SELECT pin , 'james_midkiff', addr_std , mapreg , 'test', objectid , now() 
--FROM parcel_rev_evw 
--WHERE objectid = ANY(array[777451]);

--5 - Select results
SELECT pin as "NEW PIN" , * FROM parcel_rev_evw WHERE objectid = ANY(array[777451]);

commit;

SELECT sde.sde_edit_version('james_midkiff', 2);

--
SELECT sde.sde_set_current_version('donna_short');
SELECT sde.sde_edit_version('donna_short', 1);
--select pin, addr_std , mapreg, status , *
--from parcel_rev_evw pre 
--where status in (1,3)
--order by pin desc nulls last;

select pin, addr_std , mapreg , * 
from parcel_rev_evw pre 
where status in (1,3) and pin is null
order by objectid;

select pin , addr_std , mapreg , *
from parcel_rev_evw pre
where (addr_std = '1817 RANSTEAD ST' and MAPREG = '001S110291') or
 (addr_std = '1501 E BRISTOL ST');


update parcel_rev_evw
set pin = 668
where addr_std = '1817 RANSTEAD ST' and mapreg = '001S110291';
commit;

SELECT sde.sde_edit_version('donna_short', 2);

SELECT sde.sde_set_current_version('dor');
--
SELECT sde.sde_set_current_version('joshua_graham');
SELECT sde.sde_edit_version('joshua_graham', 1);

select pin, addr_std , mapreg, status , *
from parcel_rev_evw pre 
where status in (1,3)
order by pin desc nulls last;

--select pin, addr_std , mapreg , * 
--from parcel_rev_evw pre 
--where status in (1,3) and pin is null
--order by objectid;

SELECT sde.sde_edit_version('joshua_graham', 2);
--
select * 
from (
	select pin , count(*) as count
	from parcel_rev_evw pre 
	where status in (1,3)
	group by pin
	having pin is not null 
	order by pin) as counts
where pin = ANY(ARRAY[1999001183, 1999001184]) and counts.count > 1;

--
SELECT sde.sde_set_current_version('james_midkiff');
SELECT sde.sde_edit_version('james_midkiff', 1);

update parcel_rev_evw 
set pin = 1999001341
where addr_std = '2727 RHAWN ST';

update parcel_rev_evw 
set pin = 1999001342
where addr_std = '1501 E BRISTOL ST';

commit; 
SELECT sde.sde_edit_version('james_midkiff', 2);

--
SELECT sde.sde_set_current_version('james_midkiff');
SELECT sde.sde_edit_version('james_midkiff', 1);

update parcel_rev_evw 
set pin = NULL
where addr_std = '8030 DITMAN ST' and mapreg = '160N100158';
commit;
SELECT sde.sde_edit_version('james_midkiff', 2);

-- 
select pin , addr_std , *
from parcel_rev_evw pre 
order by pin desc nulls last;

--
select pin , addr_std , mapreg , count(*) as count
from parcel_rev_evw pre 
where status in (1,3)
group by pin , addr_std , mapreg
having count(*) > 1 
order by count(*) desc;
