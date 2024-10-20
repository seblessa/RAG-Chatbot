from django.shortcuts import render
from django.http import JsonResponse
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from .models import Chunks, Document
from .serializers import DocumentSerializer
import io
# from django.http import FileResponse, Http404
# from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
# Create your views here.
import time
def get_all_docs(request):
    docs=DocumentSerializer(Document.objects.all().order_by("-created"), many=True)
    return JsonResponse(docs.data, safe=False)


CHUNK_SIZE = 25 * 1024 * 1024


class upload_chunk(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        return JsonResponse({"msg": "Method not allowed", "status": 500})

    def post(self, request, format=None):
        user = request.user
        finalized = False
        fid = request.POST.get("fileId")
        chunk = request.FILES['chunk']
        chunk_index = int(request.POST['chunkIndex'])
        file_name = request.POST['fileName']
        transcribe_id = None

        fid, obj = self.get_chunk_and_did(fid, file_name)

        # Create (or get) a temporary directory to store the chunks
        temp_dir, parent_temp_dir, chunk_name = self.create_dirs_and_check_chunks(file_name, fid, chunk_index)

        # Save the chunk
        chunk_path = os.path.join(temp_dir, chunk_name)
        default_storage.save(chunk_path, ContentFile(chunk.read()))

        # Check if all chunks are uploaded
        chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith(file_name)])
        total_chunks = len(chunk_files)

        # If all chunks are uploaded, assemble the final file
        if total_chunks * CHUNK_SIZE >= int(request.POST['fileSize']):
            final_file_buffer = self.assemble_file(chunk_files, temp_dir)

            # cleanup temp files
            os.rmdir(temp_dir)
            if not os.listdir(parent_temp_dir):
                os.rmdir(parent_temp_dir)
            obj.delete()
            finalized = True

            # Create a new TranscribePipeline instance and save the file
            transcribe_id = self.create_document_entry(final_file_buffer, file_name, user)
        return Response(
            {"msg": f"{'Upload completo!' if finalized else 'Upload em progresso...'}", "transcribe_id": transcribe_id,
             "status": finalized, "file_id": fid}, status=200)

    def get_chunk_and_did(self, did, file_name):
        '''
        ensures that a chunk entry is created or fetched.
        '''
        if did == "0":
            # not an existing upload create new chunks entry
            obj = Chunks.objects.create(originalFile=file_name)
            did = str(obj.id)
        else:
            obj = Chunks.objects.get(id=did)
        return did, obj

    def create_dirs_and_check_chunks(self, file_name, did, chunk_index):
        '''
        manages the creation of temporary directories for storing chunks.
        '''
        temp_dir = os.path.join(settings.STATIC_ROOT, 'temp_uploads', file_name, did)
        parent_temp_dir = os.path.join(settings.STATIC_ROOT, 'temp_uploads', file_name)
        os.makedirs(temp_dir, exist_ok=True)
        chunk_name = f'{file_name}_chunk_{chunk_index}'
        return temp_dir, parent_temp_dir, chunk_name

    def assemble_file(self, chunk_files, temp_dir):
        '''
        handles the assembly of the final file from the chunks
        '''
        final_file_buffer = io.BytesIO()
        for chunk_file in chunk_files:
            chunk_path = os.path.join(temp_dir, chunk_file)
            with open(chunk_path, 'rb') as temp_chunk_file:
                final_file_buffer.write(temp_chunk_file.read())
            os.remove(chunk_path)
        final_file_buffer.seek(0)
        return final_file_buffer

    def create_document_entry(self, final_file_buffer, file_name, user):
        '''
        Creates a database object representing the request for transcription with the rebuilt file.
        '''
        doc = Document(
            file=ContentFile(final_file_buffer.getvalue(), name=file_name),
            status=Document.PossibleStatus.CREATED,
            owner=user
        )
        doc.save()
        doc.init_process()
        return doc.id

