--------------------------------------------------------------------------
PNG Image Format
--------------------------------------------------------------------------

The quicklook PNG images are stored as 16-bit monochrome images with
the same metadata fields as the HDF5, prefixed with 'mango:' to
separate them from the other image metadata. You can use ImageMagick's  
identify" program to inspect the image:: 
    
    # identify --verbose mango.png

    Image: mango.png
      Format: PNG (Portable Network Graphics)
      Mime type: image/png
      Class: DirectClass
      Geometry: 695x519+0+0
      Units: Undefined
      Colorspace: Gray
      Type: Grayscale
      Base type: Undefined
      Endianess: Undefined
      Depth: 16-bit
      ...
      Properties:
        ...
        mango:bin_x: 2
        mango:bin_y: 2
        mango:bytes_per_pixel: 2
        mango:ccd_temp: -4.71000003815
        mango:device_name: Atik 414ex
        mango:exposure_time: 1.0
        mango:height: 519
        mango:image_bytes: 721410
        mango:label: Red Line
        mango:latitude: 37.454536438
        mango:longitude: -122.176055908
        mango:serialnum: 520
        mango:set_point: -5.0
        mango:start_time: 1627413300
        mango:station: cfs
        mango:version: 2
        mango:width: 695
        mango:x: 0
        mango:y: 0
    ...

