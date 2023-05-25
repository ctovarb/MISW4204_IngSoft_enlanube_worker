import os
import tempfile
import zipfile
import tarfile
from flask import current_app as app
from modelos.modelos import EstadoConversion, ExtensionFinal, TareaConversion, db
from utils import download_blob, upload_blob
import base64
import sqlalchemy


UPLOAD_FOLDER = 'uploaded-files'
PROCESSED_FOLDER = 'processed-files'

db_user = os.environ.get('POSTGRES_USER', 'postgres')
db_password = os.environ.get('POSTGRES_PASSWORD', 'admin')
db_name = os.environ.get('POSTGRES_DB', 'sistema_conversion')
db_host = os.environ.get('POSTGRES_HOST', '34.29.148.57')
db_port = os.environ.get('POSTGRES_PORT', 5432)

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def compress_file_and_update_status(tarea_id):
    tarea = TareaConversion.query.get(tarea_id)
    print(f"Attempting to compress file with ID: {tarea_id}")
    if not tarea:
        return

    tarea.estado_conversion = EstadoConversion.PROCESSING
    db.session.commit()

    try:
        # Compress the file
        compress_file(tarea)
        tarea.estado_conversion = EstadoConversion.COMPLETED

    except Exception as e:
        tarea.estado_conversion = EstadoConversion.FAILED
        print(f"Failed to compress the file: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

    db.session.commit()


def compress_file(tarea):
    # Download the uploaded file from the GCS bucket
    bucket_name = "converter_files"
    source_blob_name = f"{UPLOAD_FOLDER}/{tarea.nombre_archivo}"
    with tempfile.NamedTemporaryFile(delete=False) as temp_input_file:
        download_blob(bucket_name, source_blob_name, temp_input_file.name)
        input_file = temp_input_file.name

        # Process the output file name
        output_file = os.path.splitext(tarea.nombre_archivo)[0]

        if tarea.extension_final == ExtensionFinal.ZIP:
            output_file += '.zip'
        elif tarea.extension_final == ExtensionFinal.TAR_GZ:
            output_file += '.tar.gz'
        elif tarea.extension_final == ExtensionFinal.TAR_BZ2:
            output_file += '.tar.bz2'
        else:
            raise ValueError('Invalid compression format')

        output_blob_name = f"{PROCESSED_FOLDER}/{output_file}"

        with tempfile.NamedTemporaryFile(delete=False) as temp_output_file:
            if tarea.extension_final == ExtensionFinal.ZIP:
                with zipfile.ZipFile(temp_output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(input_file, os.path.basename(input_file))
            elif tarea.extension_final == ExtensionFinal.TAR_GZ:
                with tarfile.open(temp_output_file.name, 'w:gz') as tar:
                    tar.add(input_file, arcname=os.path.basename(input_file))
            elif tarea.extension_final == ExtensionFinal.TAR_BZ2:
                with tarfile.open(temp_output_file.name, 'w:bz2') as tar:
                    tar.add(input_file, arcname=os.path.basename(input_file))
            else:
                raise ValueError('Invalid compression format')

            temp_output_file.close()
            # Upload the output file to the GCS bucket
            upload_blob(bucket_name, temp_output_file.name, output_blob_name)
            os.remove(temp_output_file.name)

    temp_input_file.close()
    os.remove(temp_input_file.name)

    # Update the database record with the output file's blob name
    tarea.archivo_salida = output_blob_name
    db.session.commit()


def subscribe(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """

    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print('tarea_id: {}'.format(str(int(pubsub_message))))
    
    compress_file_and_update_status(int(pubsub_message))