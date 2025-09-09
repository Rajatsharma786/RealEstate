SELECT version();
SHOW data_directory; 

SELECT extname FROM pg_extension WHERE extname='vector'; 

SELECT * FROM public.langchain_pg_collection;   


SELECT substr(document,1,120) AS doc, cmetadata
FROM public.langchain_pg_embedding
LIMIT 5;

SELECT * from properties;