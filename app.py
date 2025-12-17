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

# Veri yüklemeyi önbelleğe alalım (Hız için kritik)
@st.cache_data
def load_and_clean_data(file):
    try:
        # Önce normal okumayı dene
        df = pd.read_excel(file)
        
        # Başlık kontrolü (Urun_Kodu yoksa 2. satırı dene)
        if 'Urun_Kodu' not in df.columns:
            df = pd.read_excel(file, header=1)
            
        if 'Urun_Kodu' not in df.columns:
            return None, "HATA: 'Urun_Kodu' başlığı bulunamadı."

        df.columns = df.columns.str.strip()
        
        # Fiyat sütununu bul ve temizle
        fiyat_col = [col for col in df.columns if 'Fiyat' in col]
        if fiyat_col:
            col_name = fiyat_col[0]
            
            # Hızlı temizlik fonksiyonu
            def clean_price_fast(val):
                if pd.isna(val): return 0.0
                if isinstance(val, (int, float)): return float(val)
                s = str(val)
                if "#" in s: return 0.0
                s = s.replace('€', '').replace('TL', '').replace('$', '').strip()
                if "." in s and "," in s:
                    s = s.replace('.', '').replace(',', '.')
                elif "," in s:
                    s = s.replace(',', '.')
                try:
                    return float(s)
                except:
                    return 0.0

            df[col_name] = df[col_name].apply(clean_price_fast)
            df.rename(columns={col_name: 'Fiyat'}, inplace=True)
        
        # Arama hızını artırmak için sütunları şimdiden string'e çevirelim
        df['Urun_Kodu'] = df['Urun_Kodu'].astype(str)
        df['Urun_Adi'] = df['Urun_Adi'].astype(str)
        
        return df, None
    except Exception as e:
        return None, f"Dosya okuma hatası: {e}"

if uploaded_file is not None:
    df, error_msg = load_and_clean_data(uploaded_file)
    
    if error_msg:
        st.error(error_msg)
    elif df is not None:
        st.success(f"✅ Liste Yüklendi! {len(df)} ürün hafızaya alındı.")
        
        # --- 2. Ürün Seçimi ---
        st.subheader("2. Ürün Seçimi")
        
        arama_kelimesi = st.text_input("Ürün Ara (Kod veya İsim):", "")
        
        # Fiyatı 0 olanları filtrele
        df_clean = df[df['Fiyat'] > 0]
        
        if arama_kelimesi:
            # HIZLI ARAMA: Sadece Kod ve İsim sütunlarında vektörel arama yap
            # Bu yöntem 27.000 satırda satır satır gezmekten 100 kat daha hızlıdır
            mask = (
                df_clean['Urun_Kodu'].str.contains(arama_kelimesi, case=False, na=False) | 
                df_clean['Urun_Adi'].str.contains(arama_kelimesi, case=False, na=False)
            )
            filtrelenmis_df = df_clean[mask]
        else:
            filtrelenmis_df = df_clean.head(20) # Boşken çok gösterme kasmasın

        # Seçim Kutusu
        # Listeyi oluştururken de hızlandıralım
        secenekler = filtrelenmis_df['Urun_Kodu'].tolist()
        
        secilen_urunler = st.multiselect(
            "Teklife Eklenecek Ürünleri Seç:",
            options=secenekler,
            # Format fonksiyonunu kaldırdık, çok veri olunca yavaşlatıyordu.
            # Zaten arama yapınca isim çıkıyor.
        )

        # --- 3. Hesaplama ---
        if secilen_urunler:
            st.subheader("3. Detaylar (Para Birimi: Euro)")
            
            # Seçilenleri bul (isin kullanımı çok hızlıdır)
            sepet_df = df_clean[df_clean['Urun_Kodu'].isin(secilen_urunler)].copy()
            sepet_df['Adet'] = 1
            
            # Sütun sırasını düzenle
            sepet_df = sepet_df[['Urun_Kodu', 'Urun_Adi', 'Fiyat', 'Adet']]
            sepet_df.rename(columns={'Fiyat': 'Liste_Fiyati'}, inplace=True)

            duzenlenmis_df = st.data_editor(
                sepet_df,
                column_config={
                    "Adet": st.column_config.NumberColumn("Miktar", min_value=1, step=1),
                    "Liste_Fiyati": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f €", disabled=True)
                },
                hide_index=True
            )

            col1, col2 = st.columns(2)
            with col1:
                hesap_tipi = st.radio("Yöntem:", ["İskonto (%)", "Kâr Ekle (%)"])
            with col2:
                # İSTEK: Varsayılan değer 0.0 yapıldı
                oran = st.number_input("Oran:", min_value=0.0, value=0.0, step=1.0)

            if hesap_tipi == "İskonto (%)":
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 - oran/100)
            else:
                duzenlenmis_df['Birim_Son_Fiyat'] = duzenlenmis_df['Liste_Fiyati'] * (1 + oran/100)

            duzenlenmis_df['Toplam_Tutar'] = duzenlenmis_df['Birim_Son_Fiyat'] * duzenlenmis_df['Adet']
            genel_toplam = duzenlenmis_df['Toplam_Tutar'].sum()

            st.metric(label="TOPLAM TUTAR (Euro)", value=f"€ {genel_toplam:,.2f}")

            # --- 4. İndirme ---
            if st.button("Teklif Oluştur (Excel)"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    duzenlenmis_df.to_excel(writer, index=False, sheet_name='Teklif')
                    workbook = writer.book
                    worksheet = writer.sheets['Teklif']
                    
                    para_format = workbook.add_format({'num_format': '€ #,##0.00'})
                    
                    worksheet.set_column('C:C', 15, para_format)
                    worksheet.set_column('E:F', 15, para_format)
                    worksheet.set_column('B:B', 30)

                output.seek(0)
                tarih = datetime.datetime.now().strftime("%Y-%m-%d")
                st.download_button(
                    "📥 Excel İndir (Euro)",
                    data=output,
                    file_name=f"Teklif_EURO_{tarih}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
