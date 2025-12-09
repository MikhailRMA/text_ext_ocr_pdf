{ pkgs }: {
  deps = [
    pkgs.tesseract
    pkgs.tesseract4
    pkgs.poppler_utils
    pkgs.libGL
    pkgs.libSM
    pkgs.libXext
    pkgs.libXrender
    pkgs.zlib
  ];
}