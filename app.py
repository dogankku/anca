import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Rulman Teklif Hazırlayıcı", layout="centered")

# --- Başlık ve Logo Alanı ---
st.title("🔩 Satış Ekibi Teklif Robotu")
st.write("Müşteri sahasında hızlı teklif oluşturmak için tasarlanmıştır.")

# --- 1. Veri Yükleme (Excel Dosyası) ---
# Gerçek hayatta bu dosya sabit bir yerde durabilir, şimdilik yükleme yapıyoruz.
st.subheader("1. Fiyat Listesi")
uploaded_file = st.file_uploader("Güncel Fiyat Listesini Yükle (Excel)", type=["xlsx"])

def load_data(file):
    try:
        # Excel okuma
        df = pd.read_excel(file)
        # Sütun isimlerini standartlaştıralım (Boşlukları sil vs)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        st.success(f"✅ Liste Yüklendi! Toplam {len(df)} ürün var.")
        
        # --- 2. Ürün Seçimi ve Filtreleme ---
        st.subheader("2. Ürün Seçimi")
        
        # Kullanıcı ürün kodundan veya isminden arama yapabilir
        # Varsayalım sütun adları: 'Urun_Kodu', 'Urun_Adi', 'Fiyat'
        # Eğer senin sütun adların farklıysa buraları değiştireceğiz.
        
        # Arama kutusu
        arama_kelimesi = st.text_input("Ürün Ara (Kod veya İsim):", "")
        
        if arama_kelimesi:
            # Hem kodda hem isimde arama yap
            filtrelenmis_df = df[
                df.apply(lambda row: row.astype(str).str.contains(arama_kelimesi, case=False).any(), axis=1)
            ]
        else:
            filtrelenmis_df = df.head(10) # Arama yoksa ilk 10'u göster (Mobil hızı için)

        # Seçim kutusu (Multiselect)
        secilen_urunler = st.multiselect(
            "Teklife Eklenecek Ürünleri Seç:",
            options=filtrelenmis_df['Urun_Kodu'].tolist(), # Listede görünecek kısım
            format_func=lambda x: f"{x} - {df[df['Urun_Kodu'] == x]['Urun_Adi'].values[0]}" # Daha detaylı görünüm
        )

        # --- 3. Adet ve Kâr Marjı Girişi ---
        if secilen_urunler:
            st.subheader("3. Detaylar ve Hesaplama")
            
            # Seçilenler için bir tablo oluşturuyoruz
            sepet_verisi = []
            for kod in secilen_urunler:
                satir = df[df['Urun_Kodu'] == kod].iloc[0]
                sepet_verisi.append({
                    'Urun_Kodu': satir['Urun_Kodu'],
                    'Urun_Adi': satir['Urun_Adi'],
                    'Liste_Fiyati': satir['Fiyat'], # Excel'deki ham fiyat
                    'Adet': 1 # Varsayılan adet
                })
            
            sepet_df = pd.DataFrame(sepet_verisi)

            # Kullanıcıya adetleri düzenleme imkanı ver (Data Editor - Yeni Özellik)
            duzenlenmis_df = st.data_editor(
                sepet_df,
                column_config={
                    "Adet": st.column_config.NumberColumn("Miktar", min_value=1, step=1),
                    "Liste_Fiyati": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f ₺")
                },
                hide_index=True,
                disabled=["Urun_Kodu", "Urun_Adi", "Liste_Fiyati"] # Sadece adeti değiştirsin
            )

            # İskonto veya Kâr Marjı Ayarı
            hesap_tipi = st.radio("Fiyatlandırma Yöntemi:", ["İskonto Yap (%)", "Kâr Ekle (%)"], horizontal=True)
            oran = st.slider("Oran Giriniz:", 0, 100, 10)

            # Hesaplamaları Yap
            if hesap_tipi == "İskonto Yap (%)":
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 - oran/100)
            else:
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 + oran/100)

            duzenlenmis_df['Toplam_Tutar'] = duzenlenmis_df['Birim_Son_Fiyat'] * duzenlenmis_df['Adet']
            
            genel_toplam = duzenlenmis_df['Toplam_Tutar'].sum()

            st.write("---")
            st.metric(label="GENEL TOPLAM (KDV Hariç)", value=f"{genel_toplam:,.2f} ₺")

            # --- 4. Çıktı Alma (Excel İndirme) ---
            st.subheader("4. Teklifi İndir")
            
            firma_adi = st.text_input("Müşteri Firma Adı:", "Genel Müşteri")
            
            # Excel oluşturma butonu
            if st.button("Teklif Dosyasını Oluştur"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    duzenlenmis_df.to_excel(writer, index=False, sheet_name='Teklif')
                    workbook = writer.book
                    worksheet = writer.sheets['Teklif']
                    
                    # Biraz formatlayalım
                    para_format = workbook.add_format({'num_format': '#,##0.00 ₺'})
                    worksheet.set_column('D:E', 15, para_format) # Fiyat sütunları
                    worksheet.set_column('B:B', 30) # Ürün adı geniş olsun

                output.seek(0)
                
                tarih = datetime.datetime.now().strftime("%Y-%m-%d")
                dosya_ismi = f"Teklif_{firma_adi}_{tarih}.xlsx"

                st.download_button(
                    label="📥 Excel Olarak İndir",
                    data=output,
                    file_name=dosya_ismi,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
