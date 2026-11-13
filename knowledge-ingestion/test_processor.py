"""Real local decoder tests with synthetic fixtures, not isolation qualification."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from PIL import Image
from processor import decode


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config={'workspace':str(self.root),'format':'txt','max_bytes':1048576,'max_pages':3,'max_images':1,'max_duration':1800,'interpret_images':False}

    def test_utf8_text_and_invalid_or_oversize_material(self):
        (self.root/'input').write_text('Synthetic product guide.',encoding='utf-8')
        self.assertEqual(decode(self.config)['pages'][0],{'page':1,'text':'Synthetic product guide.'})
        (self.root/'input').write_bytes(b'bad\x00text')
        with self.assertRaises(ValueError):decode(self.config)
        (self.root/'input').write_text('x'*60001,encoding='utf-8')
        with self.assertRaises(ValueError):decode(self.config)

    def test_actual_pdf_text_has_page_reference_and_encrypted_pdf_is_rejected(self):
        writer=PdfWriter();page=writer.add_blank_page(width=300,height=200)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (Synthetic PDF guide) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        writer.write(self.root/'input')
        result=decode({**self.config,'format':'pdf'})
        self.assertEqual(result['pages'][0]['page'],1);self.assertIn('Synthetic PDF guide',result['pages'][0]['text'])
        writer.encrypt('synthetic-only');writer.write(self.root/'input')
        with self.assertRaises(ValueError):decode({**self.config,'format':'pdf'})

    def test_pdf_image_export_has_private_generated_id_and_page(self):
        Image.new('RGB',(32,32),'blue').save(self.root/'input',format='PDF')
        result=decode({**self.config,'format':'pdf','interpret_images':True})
        self.assertEqual(len(result['images']),1);image=result['images'][0]
        self.assertEqual(image['page'],1);self.assertRegex(image['image_id'],r'^[0-9a-f]{32}$')
        self.assertTrue((self.root/(image['image_id']+'.png')).is_file())

    def test_docx_block_references_and_entity_rejection(self):
        xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic paragraph.</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(self.root/'input','w') as archive:archive.writestr('word/document.xml',xml)
        result=decode({**self.config,'format':'docx'})
        self.assertEqual(result['pages'][0],{'block':1,'text':'Synthetic paragraph.'})
        with zipfile.ZipFile(self.root/'input','w') as archive:archive.writestr('word/document.xml','<!DOCTYPE x>'+xml)
        with self.assertRaises(ValueError):decode({**self.config,'format':'docx'})

    def test_page_limit_and_unsupported_format_fail_closed(self):
        writer=PdfWriter()
        for _ in range(4):writer.add_blank_page(width=100,height=100)
        writer.write(self.root/'input')
        with self.assertRaises(ValueError):decode({**self.config,'format':'pdf'})
        with self.assertRaises(ValueError):decode({**self.config,'format':'html'})
