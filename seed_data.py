from database import SessionLocal, engine
import models

def seed():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # If already seeded, skip
    if db.query(models.Sector).first():
        print("Database already seeded")
        db.close()
        return

    # 1. Provide Companies
    companies = [
        models.Company(id="arzu", name="Arzu Tekstil", short_name="AT", bg_color="rgba(129,140,248,.18)", text_color="#a5b4fc"),
        models.Company(id="delta", name="Delta Geyim", short_name="DG", bg_color="rgba(93,219,168,.18)", text_color="#5ddba8"),
        models.Company(id="nova", name="Nova Fashion", short_name="NF", bg_color="rgba(245,200,66,.18)", text_color="#f5c842"),
        models.Company(id="prime", name="Prime Tekstil", short_name="PT", bg_color="rgba(240,107,107,.18)", text_color="#f06b6b"),
        models.Company(id="silk", name="Silk & Co", short_name="SC", bg_color="rgba(196,176,255,.18)", text_color="#c4b0ff"),
    ]
    db.add_all(companies)

    # 2. Provide Sectors
    sectors = [
        models.Sector(id="corab", name="Corab", icon="🧦", color_hex="#5badf0"),
        models.Sector(id="ic", name="İç Geyim", icon="👕", color_hex="#c4b0ff"),
        models.Sector(id="korp", name="İşçi geyimi", icon="👔", color_hex="#f5c842"),
    ]
    db.add_all(sectors)
    db.commit()

    # 3. Provide Stages
    stages = [
        # Corab stages
        models.Stage(id="corab-satis", sector_id="corab", name="Satış (sifariş)", capacity=10, order_index=0),
        models.Stage(id="corab-ambar", sector_id="corab", name="Anbar", capacity=14, order_index=1),
        models.Stage(id="corab-istehsal", sector_id="corab", name="İstehsalat", capacity=12, order_index=2),
        
        # İç Geyim stages
        models.Stage(id="ic-satis", sector_id="ic", name="Satış", capacity=8, order_index=0),
        models.Stage(id="ic-ambar1", sector_id="ic", name="Anbar (material təminatı)", capacity=12, order_index=1),
        models.Stage(id="ic-kesim", sector_id="ic", name="Kəsim", capacity=10, order_index=2),
        models.Stage(id="ic-tikis", sector_id="ic", name="Tikiş", capacity=12, order_index=3),
        models.Stage(id="ic-ambar2", sector_id="ic", name="Anbar", capacity=10, order_index=4),

        # İşçi geyimi stages
        models.Stage(id="korp-satis", sector_id="korp", name="Satış (sifariş)", capacity=6, order_index=0),
        models.Stage(id="korp-numune", sector_id="korp", name="Nümunə", capacity=8, order_index=1),
        models.Stage(id="korp-ambar1", sector_id="korp", name="Anbar (material təminatı)", capacity=10, order_index=2),
        models.Stage(id="korp-kesim", sector_id="korp", name="Kəsim", capacity=8, order_index=3),
        models.Stage(id="korp-tikis", sector_id="korp", name="Tikiş", capacity=10, order_index=4),
        models.Stage(id="korp-ambar2", sector_id="korp", name="Anbar", capacity=12, order_index=5),
    ]
    db.add_all(stages)

    # 4. Provide Orders
    orders = [
        # CORAB 
        models.Order(id='CR-001', sector_id='corab', company_id='arzu', product_type='Kişi Corabı', quantity='1200 cüt', stage_index=2, status='Davam edir', deadline='20 Yan', color='#5badf0', notes='Klassik iş corabı. Tünd mavi, tünd boz, qara.'),
        models.Order(id='CR-002', sector_id='corab', company_id='delta', product_type='Xanım Corabı', quantity='800 cüt', stage_index=1, status='Davam edir', deadline='22 Yan', color='#f0a0c0', notes='Dekor naxışlı. 3 rəng variasiyası.'),
        models.Order(id='CR-003', sector_id='corab', company_id='nova', product_type='İdman Corabı', quantity='600 cüt', stage_index=2, status='Tamamlandı', deadline='15 Yan', color='#5ddba8', notes='Hazır. Anbarda gözləyir.'),
        models.Order(id='CR-004', sector_id='corab', company_id='prime', product_type='Uşaq Corabı', quantity='2000 cüt', stage_index=0, status='Gözləyir', deadline='01 Fev', color='#f472b6', notes='Rəngli. Material sifariş verilib.'),
        models.Order(id='CR-005', sector_id='corab', company_id='arzu', product_type='Termal Corab', quantity='400 cüt', stage_index=1, status='Gecikmiş', deadline='10 Yan', color='#78716c', notes='Xüsusi termal iplik. 8 gün gecikib.'),
        models.Order(id='CR-006', sector_id='corab', company_id='silk', product_type='İpək Corab', quantity='150 cüt', stage_index=2, status='Davam edir', deadline='25 Yan', color='#c4b0ff', notes='Premium ipək. Əl yuyusu tövsiyə olunur.'),
        
        # IC GEYIM
        models.Order(id='IC-001', sector_id='ic', company_id='nova', product_type='Pambıq Fanes', quantity='300 əd.', stage_index=1, status='Davam edir', deadline='18 Yan', color='#f5e0c0', notes='100% pambıq. Ağ və krem rəng.'),
        models.Order(id='IC-002', sector_id='ic', company_id='arzu', product_type='Termal Köynək', quantity='180 əd.', stage_index=3, status='Davam edir', deadline='24 Yan', color='#94a3b8', notes='İkiqatlı termal toxuma. Qış üçün.'),
        models.Order(id='IC-003', sector_id='ic', company_id='delta', product_type='Xanım Pijaması', quantity='220 dəst', stage_index=2, status='Gecikmiş', deadline='12 Yan', color='#f472b6', notes='Çiçəkli çap. Kəsim mərhələsində gecikib.'),
        models.Order(id='IC-004', sector_id='ic', company_id='silk', product_type='İpək Gecəlik', quantity='80 əd.', stage_index=4, status='Davam edir', deadline='27 Yan', color='#c4b0ff', notes='Premium satin. Lüks qablaşdırma tələb olunur.'),
        models.Order(id='IC-005', sector_id='ic', company_id='prime', product_type='Kişi Mayosu', quantity='500 əd.', stage_index=0, status='Gözləyir', deadline='03 Fev', color='#5badf0', notes='Yay sifariş. Material gözlənilir.'),
        models.Order(id='IC-006', sector_id='ic', company_id='nova', product_type='Boks Paltarı', quantity='250 dəst', stage_index=4, status='Tamamlandı', deadline='14 Yan', color='#5ddba8', notes='Hazır. Çatdırılma gözləyir.'),
        
        # ISCI GEYIMI
        models.Order(id='KP-001', sector_id='korp', company_id='prime', product_type='İş Köynəyi', quantity='150 əd.', stage_index=3, status='Davam edir', deadline='22 Yan', color='#1e3a5f', notes='ABC Şirkəti üçün. Döş logo, ön cib.'),
        models.Order(id='KP-002', sector_id='korp', company_id='delta', product_type='Uniform Kostyum', quantity='60 dəst', stage_index=1, status='Gecikmiş', deadline='08 Yan', color='#1e293b', notes='Mühafizə şirkəti. Xüsusi qiymət davamlı qumaş.'),
        models.Order(id='KP-003', sector_id='korp', company_id='arzu', product_type='Polo Köynək', quantity='200 əd.', stage_index=4, status='Davam edir', deadline='26 Yan', color='#0f4c75', notes='IT şirkəti. Bel logolu. 4 ölçü.'),
        models.Order(id='KP-004', sector_id='korp', company_id='silk', product_type='Qalay Kravat', quantity='100 əd.', stage_index=2, status='Davam edir', deadline='20 Yan', color='#c4b0ff', notes='Bank sifariş. İpək kravat. Monoqram.'),
        models.Order(id='KP-005', sector_id='korp', company_id='nova', product_type='Xanım Jaketi', quantity='40 əd.', stage_index=0, status='Gözləyir', deadline='05 Fev', color='#1a1a2e', notes='Hüquq bürosu. Rəsmi üslub.'),
        models.Order(id='KP-006', sector_id='korp', company_id='prime', product_type='Yeleksiz Forma', quantity='80 dəst', stage_index=5, status='Tamamlandı', deadline='10 Yan', color='#5ddba8', notes='Restoran forması. Çatdırılmağa hazır.'),
    ]
    db.add_all(orders)

    db.commit()
    db.close()
    print("Database seeded successfully with initial data.")

if __name__ == "__main__":
    seed()
