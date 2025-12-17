import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Rulman Teklif Hazırlayıcı", layout="centered")

st.title("🔩 Satış Ekibi Teklif Robotu")
st.write("Müşteri sahasında hızlı teklif oluşturmak için tasarlanmıştır.")

# --- 1. Veri Yükleme ---
st.subheader("1. Fiyat Listesi")
uploaded_file = st.file_uploader("Güncel Fiyat Listesini Yükle (Excel)", type=["xlsx"])

def clean_price(price):
    """Fiyat sütunundaki €, TL gibi yazıları ve hataları temizler."""
    if pd.isna(price):
        return 0.0
    
    price_str = str(price)
    
    # Excel hatalarını (#DEĞER!, #SAYI! vs) kontrol et
    if "#" in price_str:
        return 0.0
        
    # Para birimi simgelerini ve boşlukları temizle
    price_str = price_str.replace('€', '').replace('TL', '').replace('$', '').strip()
    
    # Türkiye formatı (1.000,00) -> Python formatı (1000.00) dönüşümü
    # Önce binlik ayıracı olan noktayı kaldır
    price_str = price_str.replace('.', '')
    # Sonra ondalık ayıracı olan virgülü noktaya çevir
    price_str = price_str.replace(',', '.')
    
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def load_data(file):
    try:
        # Önce normal okumayı dene
        df = pd.read_excel(file)
        
        # Eğer 'Urun_Kodu' başlığı bulunamazsa, muhtemelen başlıklar 2. satırdadır.
        # Bir satır atlayarak tekrar oku.
        if 'Urun_Kodu' not in df.columns:
            df = pd.read_excel(file, header=1)
            
        # Hala bulunamadıysa hata ver
        if 'Urun_Kodu' not in df.columns:
            st.error("HATA: Excel dosyasında 'Urun_Kodu' sütunu bulunamadı. Başlıkların doğru yazıldığından emin olun.")
            return None

        # Sütun isimlerindeki boşlukları temizle
        df.columns = df.columns.str.strip()
        
        # Fiyat sütununu temizle ve sayıya çevir
        # Fiyat sütununun adını bul (Bazen boşluklu olabilir 'Fiyat ' gibi)
        fiyat_col = [col for col in df.columns if 'Fiyat' in col]
        if fiyat_col:
            col_name = fiyat_col[0]
            df[col_name] = df[col_name].apply(clean_price)
            # Kolaylık olsun diye adını standartlaştıralım
            df.rename(columns={col_name: 'Fiyat'}, inplace=True)
            
        return df
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        st.success(f"✅ Liste Yüklendi! Toplam {len(df)} ürün var.")
        
        # --- 2. Ürün Seçimi ---
        st.subheader("2. Ürün Seçimi")
        
        arama_kelimesi = st.text_input("Ürün Ara (Kod veya İsim):", "")
        
        # Fiyatı 0 olanları (Hatalı satırları) aramada gösterme
        df_clean = df[df['Fiyat'] > 0]
        
        if arama_kelimesi:
            filtrelenmis_df = df_clean[
                df_clean.apply(lambda row: row.astype(str).str.contains(arama_kelimesi, case=False).any(), axis=1)
            ]
        else:
            filtrelenmis_df = df_clean.head(10)

        # Seçim Kutusu
        secilen_urunler = st.multiselect(
            "Teklife Eklenecek Ürünleri Seç:",
            options=filtrelenmis_df['Urun_Kodu'].tolist(),
            format_func=lambda x: f"{x} - {df_clean[df_clean['Urun_Kodu'] == x]['Urun_Adi'].values[0]}"
        )

        # --- 3. Hesaplama ---
        if secilen_urunler:
            st.subheader("3. Detaylar")
            
            sepet_verisi = []
            for kod in secilen_urunler:
                satir = df_clean[df_clean['Urun_Kodu'] == kod].iloc[0]
                sepet_verisi.append({
                    'Urun_Kodu': satir['Urun_Kodu'],
                    'Urun_Adi': satir['Urun_Adi'],
                    'Liste_Fiyati': satir['Fiyat'],
                    'Adet': 1
                })
            
            sepet_df = pd.DataFrame(sepet_verisi)

            duzenlenmis_df = st.data_editor(
                sepet_df,
                column_config={
                    "Adet": st.column_config.NumberColumn("Miktar", min_value=1, step=1),
                    "Liste_Fiyati": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f ₺")
                },
                hide_index=True,
                disabled=["Urun_Kodu", "Urun_Adi", "Liste_Fiyati"]
            )

            col1, col2 = st.columns(2)
            with col1:
                hesap_tipi = st.radio("Yöntem:", ["İskonto (%)", "Kâr Ekle (%)"])
            with col2:
                oran = st.number_input("Oran:", min_value=0.0, value=10.0)

            if hesap_tipi == "İskonto (%)":
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 - oran/100)
            else:
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 + oran/100)

            duzenlenmis_df['Toplam_Tutar'] = duzenlenmis_df['Birim_Son_Fiyat'] * duzenlenmis_df['Adet']
            genel_toplam = duzenlenmis_df['Toplam_Tutar'].sum()

            st.metric(label="TOPLAM TUTAR", value=f"{genel_toplam:,.2f} ₺")

            # --- 4. İndirme ---
            if st.button("Teklif Oluştur (Excel)"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    duzenlenmis_df.to_excel(writer, index=False, sheet_name='Teklif')
                    workbook = writer.book
                    worksheet = writer.sheets['Teklif']
                    para_format = workbook.add_format({'num_format': '#,##0.00 ₺'})
                    worksheet.set_column('C:E', 15, para_format)
                    worksheet.set_column('B:B', 30)

                output.seek(0)
                tarih = datetime.datetime.now().strftime("%Y-%m-%d")
                st.download_button(
                    "📥 Excel İndir",
                    data=output,
                    file_name=f"Teklif_{tarih}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
