import geopandas as gpd
import matplotlib.pyplot as plt
import folium

# Shapefile のパスを指定
shapefile_path = "/Users/nakashima/Downloads/shape_佐賀_コメ収量（収量重視）［S-8］/Saga_AgricultureRiceAdp0_CMIP5RCP85_MRI_No.shp"  # .shpファイルへのパス

# Shapefile を読み込む
gdf = gpd.read_file(shapefile_path)

# データの表示
print(gdf.head())

# Shapefile の可視化
gdf.plot()
plt.show()

# # Shapefile の読み込み（先ほどのgdf）
# m = folium.Map(location=[35.0, 135.0], zoom_start=5)

# # GeoDataFrameをfoliumで表示
# folium.GeoJson(gdf).add_to(m)

# # インタラクティブな地図を表示
# m.save("map.html")