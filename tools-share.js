/* Shared "Share This Tool" widget for every tools/*.html page.
   Each tool page just needs:
     <div id="tsj-tool-share" style="margin:16px 15px"></div>
     <link rel="stylesheet" href="/tools-share.css">
     <script src="/tools-share.js" defer></script>
   Tool name + pitch line are looked up by pathname below so no per-page
   customization is needed in the HTML itself — mirrors the dh-share-btns
   component already used on job detail pages, but with tool-specific
   copy instead of job-specific fields (fee/posts/last date don't apply
   here). */
(function () {
  var TOOL_SHARE_DATA = {
    '/tools/image/background-remove.html': { name: 'Background Remover', pitch: 'Photo ka background 1-click me remove karke transparent ya white banayein' },
    '/tools/image/bulk-image-resize.html': { name: 'Bulk Image Resize', pitch: 'Ek saath multiple photos resize karein, ek-ek karke time waste mat karein' },
    '/tools/image/compress-image.html': { name: 'Compress Image', pitch: 'Photo ki file size KB me kam karein — form upload ke liye perfect' },
    '/tools/image/convert-any-format.html': { name: 'Image Format Converter', pitch: 'JPG, PNG, WEBP, HEIC — kisi bhi format me photo convert karein' },
    '/tools/image/document-scanner.html': { name: 'Document Scanner', pitch: 'Mobile camera se document scan karein, PDF banayein, OCR se text bhi nikaalein' },
    '/tools/image/heic-to-jpg.html': { name: 'HEIC to JPG Converter', pitch: 'iPhone ki HEIC photo ko turant JPG me convert karein' },
    '/tools/image/image-merge.html': { name: 'Image Merge', pitch: 'Multiple photos ko ek single image ya A4 print sheet me combine karein' },
    '/tools/image/image-resizer.html': { name: 'Image Resizer', pitch: 'Photo ko exact pixel size me resize karein — form upload ke liye perfect' },
    '/tools/image/image-to-pdf.html': { name: 'Image to PDF', pitch: 'Photos ko ek click me PDF file me convert karein' },
    '/tools/image/jpg-to-png.html': { name: 'JPG to PNG Converter', pitch: 'JPG photo ko turant PNG me convert karein' },
    '/tools/image/passport-photo.html': { name: 'Passport Photo Maker', pitch: 'Passport/form size photo banayein, background change karein — print-ready size' },
    '/tools/image/photo-editor.html': { name: 'Photo Editor', pitch: 'Photo crop, rotate aur edit karein — bilkul free, online' },
    '/tools/image/photo-enhancer.html': { name: 'AI Photo Enhancer', pitch: 'Blurry/purani photo ko AI se sharp aur clear banayein' },
    '/tools/image/png-to-jpg.html': { name: 'PNG to JPG Converter', pitch: 'PNG image ko turant JPG me convert karein' },
    '/tools/image/signature-resizer.html': { name: 'Signature Resizer', pitch: 'Signature ko form ke exact KB/size me resize karein' },
    '/tools/image/webp-to-jpg.html': { name: 'WEBP to JPG Converter', pitch: 'WEBP image ko turant JPG me convert karein' },

    '/tools/av/audio-convert.html': { name: 'Audio Format Converter', pitch: 'Audio file ka format 1-click me convert karein' },
    '/tools/av/audio-merge.html': { name: 'Audio Merge', pitch: 'Multiple audio files ko ek saath combine karein' },
    '/tools/av/audio-studio.html': { name: 'Audio Studio', pitch: 'AI Voice Enhance, Background Noise Removal, Equalizer — sab kuch free' },
    '/tools/av/audio-trim.html': { name: 'Audio Trim', pitch: 'Audio file ko cut/trim karein, bilkul free online' },
    '/tools/av/screen-recorder.html': { name: 'Screen Recorder', pitch: 'Apni screen record karein, koi app install kiye bina' },
    '/tools/av/video-compress.html': { name: 'Video Compress', pitch: 'Video file size kam karein, quality maintain rakhte hue' },
    '/tools/av/video-convert.html': { name: 'Video Convert', pitch: 'Video format 1-click me convert karein' },
    '/tools/av/video-editor.html': { name: 'Video Editor', pitch: 'Videos merge, trim aur edit karein — bilkul free' },
    '/tools/av/video-studio.html': { name: 'Video Studio', pitch: 'Live video editor — text, effects, crop, sab ek jagah' },
    '/tools/av/video-to-mp3.html': { name: 'Video to MP3', pitch: 'Video se MP3 audio extract karein' },
    '/tools/av/video-trim.html': { name: 'Video Trim', pitch: 'Video ko cut/trim karein, bilkul free online' },

    '/tools/pdf/add-watermark.html': { name: 'Add Watermark to PDF', pitch: 'PDF me text/image watermark add karein' },
    '/tools/pdf/any-file-to-pdf.html': { name: 'Any File to PDF', pitch: 'Kisi bhi file ko PDF me convert karein' },
    '/tools/pdf/compress-pdf.html': { name: 'Compress PDF', pitch: 'PDF file size kam karein — form upload ke liye ready' },
    '/tools/pdf/merge-pdf.html': { name: 'Merge PDF', pitch: 'Multiple PDF files ko ek me combine karein' },
    '/tools/pdf/pdf-lock.html': { name: 'Lock PDF', pitch: 'PDF file ko password se protect karein' },
    '/tools/pdf/pdf-to-any-format.html': { name: 'PDF to Any Format', pitch: 'PDF ko kisi bhi format me convert karein' },
    '/tools/pdf/pdf-to-word.html': { name: 'PDF to Word', pitch: 'PDF ko editable Word document me convert karein' },
    '/tools/pdf/pdf-unlock.html': { name: 'Unlock PDF', pitch: 'PDF se password protection remove karein' },
    '/tools/pdf/reorder-pdf.html': { name: 'Reorder PDF Pages', pitch: 'PDF ke pages ka order rearrange karein' },
    '/tools/pdf/rotate-pdf.html': { name: 'Rotate PDF', pitch: 'PDF ke pages rotate karein' },
    '/tools/pdf/sign-pdf.html': { name: 'Sign PDF', pitch: 'PDF document par e-signature add karein' },
    '/tools/pdf/split-pdf.html': { name: 'Split PDF', pitch: 'PDF ko separate pages/files me split karein' }
  };

  function deriveNameFromTitle() {
    var t = document.title || 'Free Tool';
    return t.split(/[–—|]/)[0].trim() || 'Free Tool';
  }

  function buildMessage(name, pitch, url) {
    var lines = [
      '🛠️ Form Bharte Time Problem Aaye? ',
      '🚨 Free Online Tool: ' + name,
      '',
      '⚡ ' + pitch + '!',
      '',
      '🎯 Safe, Fast & Easy Online Tool:',
      '👉 ' + url,
      '',
      '🔔 Abhi Try Karein Aur Apne Dosto Ke Saath Bhi Share Karein!',
      '#Topsarkarijobs #Topsarkarijob'
    ];
    return lines.join('\n');
  }

  function init() {
    var mount = document.getElementById('tsj-tool-share');
    if (!mount) return;

    var data = TOOL_SHARE_DATA[location.pathname] || {};
    var name = data.name || deriveNameFromTitle();
    var pitch = data.pitch || 'Form me Photo/Signature Resize karna ho ya Age Calculate karni ho—ab sab hoga 1-Click me bilkul FREE';
    var canonEl = document.querySelector('link[rel="canonical"]');
    var url = (canonEl && canonEl.href) || location.href;

    var msg = buildMessage(name, pitch, url);
    var encMsg = encodeURIComponent(msg);
    var encUrl = encodeURIComponent(url);

    mount.innerHTML =
      '<div class="dh-share">' +
      '<span class="dh-share-lbl">🔗 Share This Tool</span>' +
      '<div class="dh-share-btns">' +
      '<a href="https://api.whatsapp.com/send?text=' + encMsg + '" target="_blank" rel="noopener" class="dh-sh wa" aria-label="Share on WhatsApp">💬</a>' +
      '<a href="https://t.me/share/url?url=' + encUrl + '&text=' + encMsg + '" target="_blank" rel="noopener" class="dh-sh tg" aria-label="Share on Telegram">✈️</a>' +
      '<a href="https://www.facebook.com/sharer/sharer.php?u=' + encUrl + '" target="_blank" rel="noopener" class="dh-sh fb" aria-label="Share on Facebook">📘</a>' +
      '<a href="https://twitter.com/intent/tweet?text=' + encMsg + '" target="_blank" rel="noopener" class="dh-sh tw" aria-label="Share on X">✖️</a>' +
      '<a href="https://www.linkedin.com/sharing/share-offsite/?url=' + encUrl + '" target="_blank" rel="noopener" class="dh-sh li" aria-label="Share on LinkedIn">💼</a>' +
      '<button type="button" class="dh-sh cp" aria-label="Copy details">🔗</button>' +
      '</div></div>';

    var cp = mount.querySelector('.dh-sh.cp');
    if (cp) {
      cp.addEventListener('click', function () {
        function done() {
          cp.textContent = '✅';
          setTimeout(function () { cp.textContent = '🔗'; }, 1500);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(msg).then(done).catch(function () {});
        }
      });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
