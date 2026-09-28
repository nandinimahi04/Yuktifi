import React from 'react';
import { ChevronLeft, ArrowRight, ChevronDown, Lightbulb } from 'lucide-react';
import { useTranslations } from 'next-intl';

const BUSINESS_IDEAS: Record<string, {title: string, desc: string}[]> = {
  'Retail & Shop': [
    { title: 'Specialty Grocery & Mini-Mart', desc: 'A modernised Kirana store offering local staples alongside packaged FMCG goods, with digital payment and local WhatsApp delivery.' },
    { title: 'Agri-Hardware & Tools Shop', desc: 'Selling seeds, fertilizers, small farming implements, and drip-irrigation spare parts to local farmers.' },
    { title: 'Pooja Samagri & Festival Store', desc: 'A dedicated shop for religious items, incense, seasonal festival decorations, and locally sourced flowers.' }
  ],
  'Manufacturing': [
    { title: 'Paper Plate & Cup Manufacturing', desc: 'A low-capex unit using semi-automatic machines to produce eco-friendly paper tableware for local caterers and food stalls.' },
    { title: 'Spice (Masala) Processing & Packaging', desc: 'Buying whole spices from the wholesale market, grinding them in a local mill setup, and packaging them under a local brand.' },
    { title: 'Chaddar / Towel Powerloom Unit', desc: 'Setting up 2-4 powerlooms to manufacture cotton towels or bedsheets as a supplier to larger wholesale markets.' }
  ],
  'Agri-Business': [
    { title: 'Dairy Farming & Milk Collection', desc: 'Setting up a small shed with 5-10 high-yield buffaloes/cows and acting as a local milk collection hub for larger dairies.' },
    { title: 'Poultry Farming (Broiler/Layer)', desc: 'A contract farming setup or independent shed for egg and meat production, supplying local butchers and restaurants.' },
    { title: 'Mushroom Cultivation', desc: 'Low-space, controlled-environment farming of oyster or button mushrooms to supply local hotels and supermarkets.' }
  ],
  'Services & Tech': [
    { title: 'CSC / Maha-e-Seva Kendra', desc: 'A digital shop offering printing, PAN card applications, Aadhaar updates, scheme enrollments, and money transfer services.' },
    { title: 'Two-Wheeler & Tractor Repair Garage', desc: 'A modernized auto-repair shop focusing on bikes and agricultural vehicles, keeping spare parts in stock.' },
    { title: 'Mobile Repair & Accessories Shop', desc: 'Fixing smartphones, selling chargers/covers, and offering mobile recharge or second-hand phone sales.' }
  ],
  'Food & Beverage': [
    { title: 'Cloud Kitchen / Tiffin Service', desc: 'Supplying affordable, home-cooked daily meals to students, bank employees, and shop workers.' },
    { title: 'Flour & Oil Mill (Chakki)', desc: 'A community mill where locals bring their grains and oilseeds to be ground or pressed for a service fee.' },
    { title: 'Specialty Snacks / Bakery', desc: 'Making local snacks (like chiwda, farsan) or baked goods (pav, khari) in bulk to distribute to local tea stalls and Kirana shops.' }
  ],
  'Handicrafts & Artisanal': [
    { title: 'Handloom Weaving & Tailoring', desc: 'Crafting specialized local garments, customized tailoring for women\'s wear, or creating embroidered textiles.' },
    { title: 'Bamboo & Cane Furniture Making', desc: 'Crafting affordable chairs, baskets, and decorative items from locally sourced bamboo.' },
    { title: 'Pottery & Clay Products', desc: 'Modernizing traditional pottery to create eco-friendly clay cups (kulhads), water filters, and decorative diyas.' }
  ],
  'Logistics & Delivery': [
    { title: 'Last-Mile Courier Franchise', desc: 'Taking a franchise of Delhivery, Ecom Express, or DTDC to handle local e-commerce package deliveries.' },
    { title: 'Agri-Transport Service', desc: 'Buying a small commercial vehicle (like a Tata Ace / Chota Hathi) to transport vegetables and grains from farms to the market yard (Mandi).' },
    { title: 'Local Goods Moving', desc: 'Providing relocation and material transport services for small shops and households within the city limits.' }
  ],
  'Education & Training': [
    { title: 'Computer & Typing Institute', desc: 'Teaching basic digital literacy, MS Office, Tally (for accounting), and regional language typing to local youth.' },
    { title: 'Tuition & Coaching Centre', desc: 'After-school coaching for school children (Math, Science, English) or preparation for government job exams (MPSC/Police Bharti).' },
    { title: 'Vocational Skill Centre', desc: 'A small workshop teaching practical skills like basic electronics repair, sewing, or beautician courses.' }
  ],
  'Healthcare & Wellness': [
    { title: 'Generic Medicine Store (Jan Aushadhi Kendra)', desc: 'A pharmacy focusing on affordable generic medicines, basic first aid, and wellness supplements.' },
    { title: 'Diagnostic Collection Centre', desc: 'A small storefront where patients can give blood/urine samples, which you transport to a larger pathology lab in the city.' },
    { title: 'Beauty Parlour & Salon', desc: 'A neighbourhood salon offering affordable grooming, bridal makeup, and wellness services.' }
  ],
  'Fashion & Apparel': [
    { title: 'Readymade Garment Shop', desc: 'Selling affordable, trendy clothing sourced from wholesale hubs (like Mumbai or Surat) to the local youth and families.' },
    { title: 'School Uniform & Workwear Manufacturing', desc: 'Stitching bulk orders of uniforms for local schools, factory workers, and hospital staff.' },
    { title: 'Imitation Jewellery & Cosmetics Store', desc: 'A boutique selling affordable artificial jewellery, bangles, and cosmetic products for daily wear and weddings.' }
  ]
};

export interface BusinessData {
  industry: string;
  experience: string;
  ideaDetails: string;
}

interface StepBusinessProps {
  data: BusinessData;
  updateData: (updates: Partial<BusinessData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepBusiness({ data, updateData, onNext, onBack }: StepBusinessProps) {
  const t = useTranslations('onboarding.step4');
  const tCommon = useTranslations('common');
  
  const PREDEFINED_INDUSTRIES = [
    { value: 'Retail & Shop', label: t('indRetail') },
    { value: 'Manufacturing', label: t('indMfg') },
    { value: 'Agri-Business', label: t('indAgri') },
    { value: 'Services & Tech', label: t('indServices') },
    { value: 'Food & Beverage', label: t('indFood') },
    { value: 'Handicrafts & Artisanal', label: t('indCrafts') },
    { value: 'Logistics & Delivery', label: t('indLogistics') },
    { value: 'Education & Training', label: t('indEdu') },
    { value: 'Healthcare & Wellness', label: t('indHealth') },
    { value: 'Fashion & Apparel', label: t('indFashion') }
  ];
  
  const predefinedValues = PREDEFINED_INDUSTRIES.map(i => i.value);
  const isCustomIndustry = data.industry !== '' && !predefinedValues.includes(data.industry);
  
  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-4 sm:p-6 border border-premium-border shadow-card relative overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 pr-2">
        <h2 className="text-[28px] font-bold text-forest-deep mb-1 font-display">{t('title')}</h2>
        <p className="text-ink-soft text-sm font-medium mb-4">
          {t('subtitle')}
        </p>

        <div className="space-y-4">
          
          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('industry')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="relative">
              <select
                className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink bg-white appearance-none focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all cursor-pointer font-medium"
                value={isCustomIndustry ? 'Other' : data.industry}
                onChange={(e) => {
                  if (e.target.value === 'Other') {
                    updateData({ industry: 'Custom' });
                  } else {
                    updateData({ industry: e.target.value });
                  }
                }}
              >
                <option value="" disabled>{t('selectIndustry')}</option>
                {PREDEFINED_INDUSTRIES.map(ind => (
                  <option key={ind.value} value={ind.value}>{ind.label}</option>
                ))}
                <option value="Other">{t('otherSpecify')}</option>
              </select>
              <ChevronDown className="absolute right-4 top-2.5 text-ink-soft pointer-events-none" size={20} />
            </div>

            {isCustomIndustry && (
              <div className="pt-2 animate-in fade-in slide-in-from-top-2 duration-300">
                <input 
                  type="text"
                  placeholder={t('otherPlaceholder')}
                  className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all"
                  value={data.industry === 'Custom' ? '' : data.industry}
                  onChange={(e) => updateData({ industry: e.target.value })}
                  autoFocus
                />
              </div>
            )}

            {data.industry && BUSINESS_IDEAS[data.industry] && (
              <div className="pt-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                <label className="text-sm font-bold text-ink flex items-center">
                  <Lightbulb size={16} className="text-[#ea580c] mr-2" />
                  {t('suggestedIdeas')}
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {BUSINESS_IDEAS[data.industry].map((idea, idx) => (
                    <div 
                      key={idx}
                      onClick={() => updateData({ ideaDetails: `${idea.title}:\n${idea.desc}` })}
                      className="p-2 border border-premium-border rounded-xl cursor-pointer hover:border-forest hover:bg-forest-tint/10 transition-all text-left group shadow-sm hover:shadow"
                    >
                      <h4 className="text-sm font-bold text-forest-deep mb-1 group-hover:text-forest transition-colors">{idea.title}</h4>
                      <p className="text-xs text-ink-soft leading-tight">{idea.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('idea')}
            </label>
            <textarea 
              rows={2}
              placeholder={t('ideaPlaceholder')}
              className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all resize-none"
              value={data.ideaDetails || ''}
              onChange={(e) => updateData({ ideaDetails: e.target.value })}
            />
          </div>
          
          <div className="space-y-2 pt-4">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('experience')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'None, I am a beginner', label: t('expNone') },
                { value: '1-3 Years', label: t('exp1to3') },
                { value: '3-5 Years', label: t('exp3to5') },
                { value: '5+ Years', label: t('exp5plus') }
              ].map(option => (
                <label key={option.value} className={`flex items-center px-4 py-2 rounded-xl border cursor-pointer transition-colors ${data.experience === option.value ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold' : 'border-premium-border hover:bg-cream text-ink font-medium'}`}>
                  <input 
                    type="radio" 
                    name="experience" 
                    value={option.value}
                    className="mr-3 w-4 h-4 accent-forest"
                    checked={data.experience === option.value}
                    onChange={() => updateData({ experience: option.value })}
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Footer Nav */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-premium-border">
        <button 
          onClick={onBack}
          className="flex items-center text-ink-soft hover:text-ink font-bold text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1"
        >
          <ChevronLeft size={18} className="mr-1" /> {tCommon('back')}
        </button>
        
        <button 
          onClick={onNext}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-8 py-2 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
