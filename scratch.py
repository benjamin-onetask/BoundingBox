from google.cloud import firestore, storage
from firebase_admin import credentials, initialize_app

from configs import BUCKET_NAME, CREDENTIALS_PATH, QUERY_THRESHOLD


def gcp_query_download():

    cred = credentials.Certificate(CREDENTIALS_PATH)
    initialize_app(cred)

    db = firestore.Client()
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(BUCKET_NAME)
    sightings_ref = db.collection("sightings")

    image_count = 0

    # query_date_from = self.get_date()
    query = sightings_ref.where(filter=firestore.FieldFilter("date", ">=", "2023-12-10"))
    # query = sightings_ref.where(filter=firestore.FieldFilter("is_processed_any_positive", "==", True))

    # Check for is_labelled -> this will be set to true after the image has been labelled
    # query = sightings_ref.where(filter=firestore.FieldFilter("is_labelled", "!=", True))
    if QUERY_THRESHOLD:
        query = query.limit(QUERY_THRESHOLD)

    sightings_docs = query.get()

    for doc in sightings_docs:
        doc_data = doc.to_dict()
        sighting_id = doc_data.get("sighting_id")
        print(sighting_id)
        # try:
        #     doc_data = doc.to_dict()
        #     sighting_id = doc_data.get("sighting_id")
        #     taken_on = doc_data.get("taken_on")
        #     date = doc_data.get("date")
        #     time = doc_data.get("time")

        #     face_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_FACE.jpg"
        #     wscr_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_WSCR.jpg"
        #     # lp_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_LP.jpg"

        #     self.download_helper(bucket, face_image_name)
        #     self.download_helper(bucket, wscr_image_name)

        # except Exception as e:
        #     print(f"Error downloading images for sighting {sighting_id}, {e}")
        #     continue

gcp_query_download()