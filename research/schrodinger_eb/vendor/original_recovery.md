# Recuperação auditável das fontes originais do etilbenzeno

Data da investigação: 10 de outubro de 2026. Este arquivo registra recuperação de fontes, não uma reprodução executada do Matlab/Aspen.

## Fontes inspecionadas

1. Google Drive, `Dropbox - Mestrado e TFC` → `MESTRADO_WALTER` → `MONOGRAFIA - TCC`, incluindo `etilbenzeno`, `FILTRO_KALMAN`, `WORKSHOP_CT_FK` e `REVISAO_PROFESSOR`.
2. Arquivo `TFC.zip`, 87.482.961 bytes, encontrado em outra pasta `TFC` e baixado integralmente. A lista completa de seus 232 itens foi salva em `research/original_tfc/recovered/TFC_zip_manifest.json`.
3. Artigo original `Luyben-2011-AIChE_Journal (1).pdf`, baixado e convertido para texto local como `Luyben_2011.pdf` e `Luyben_2011.txt`.
4. Arquivo `Filtro_de_Kalman.zip`, 1.212.067 bytes, listado integralmente. Contém exemplo didático anterior (2007–2009), não o reator de etilbenzeno.
5. A pasta `DISSERTACAO_WALTER/SIMULINK` contém arquivos do CSTR de propilenoglicol. Não são um substituto para o modelo histórico de etilbenzeno.

URLs de origem:

- Pasta original: https://drive.google.com/drive/folders/10s8gvy2ekd_awxCRhxvz3gWlWDba7avh
- TFC.zip: https://drive.google.com/file/d/1lIkJrb7TEWfhAqIf6GVyMFGSJahAXmo2/view
- Luyben 2011: https://drive.google.com/file/d/18FJIrXtZbzlPBg2B1bFmQ9ZYq45-ISIe/view
- Modelo Aspen antigo: https://drive.google.com/file/d/1YI96QJHWtcOZ-SvD0NW8JVaIwl7CTSVz/view

## Achados críticos

### Cinética e estequiometria verificadas em fonte primária

O artigo Luyben (2011), tabela 1, apresenta fatores pré-exponenciais `[1.528e6, 2.778e7, 1000]` e energias `[17000, 20000, 15000]` cal/mol. Os termos de concentração são `CE*CB`, `CE*CEB` e `CB*CDEB`, em kmol/m³. É necessário resolver a unidade temporal efetiva antes de transplantar os números para um ODE em horas.

O arquivo original `TFC.zip/AspenSimFiles/Ethylbenzene_walter/Ethylbenzene.bkp` confirma exatamente esses fatores e energias, com três reações, e confirma coeficiente estequiométrico **2** para o etilbenzeno na transalquilação. O documento original `Modelagem e equações.docx` também confirma `rEB = k1*CE*CB - k2*CE*CEB + 2*k3*CB*CDEB`.

### Versões Aspen não são intercambiáveis

`aspeneb.bkp`, encontrado na pasta de monografia e também em `TFC.zip/ASPEN`, é uma versão antiga datada de junho de 2016. Usa temperatura 160 °C, pressão 9 bar, k2=27780 e k3=0.4167. **Não é o mesmo modelo** que `AspenSimFiles/Ethylbenzene_walter/Ethylbenzene.bkp`, o qual usa T=434 K, P=20 atm, k2=27780000 e k3=1000. A confusão entre os dois impediria uma reprodução válida.

Na versão consistente com Luyben, ambos os reatores têm volume de líquido 200 m³. O primeiro é especificado com 434 K e 20 atm; o segundo com 432 K e 19 atm. Alimentações frescas: benzeno e etileno 630,6 kmol/h cada, T=320 K. Coluna 1: 20 estágios, alimentação estágio 10, pressão de topo 0,3 atm, destilado 969,4 kmol/h e razão de refluxo 0,774. Coluna 2: 24 estágios, alimentação estágio 15, topo 0,1 atm, fundo 282,2 kmol/h e razão de refluxo 0,661.

Os resultados armazenados para o CSTR1 indicam saída total 1606,15065 kmol/h, etileno 6,25720598, benzeno 1055,62916, EB 463,900029 e DEB 80,364254 kmol/h. As frações correspondentes são aproximadamente `[0.00389578, 0.65724168, 0.28882721, 0.05003534]`, coerentes com a coluna Aspen do TFC. Essas são **saídas históricas armazenadas**; Aspen não foi executado nesta investigação.

### O código final FKE + PI não foi encontrado nas fontes recuperadas

No TFC.zip, os únicos códigos MATLAB são `Matlab/FK_temp_exemplo.m` e uma cópia de conflito. São um exemplo escalar de temperatura, não o reator. O único Simulink, `Simulink/FiltroKalman.slx`, também é um exemplo escalar (gerador aleatório com média 72), não o modelo químico final.

Não foram recuperados o Q térmico ajustado do Matlab, os ganhos PI originais, as matrizes Q/R/P0 do FKE final, a amostragem final ou os vetores históricos de trajetória e cálculo de métricas. Não atribuir parâmetros inventados a 2016, nem usar a sintonia dos exemplos como baseline.

O arquivo maior `MESTRADO_WALTER.zip` tem 437.968.749 bytes e a tentativa de download retornou limite de tamanho de 268.435.456 bytes do serviço. A pasta já descompactada foi inspecionada como alternativa. Nenhuma alteração externa foi realizada.

## Consequência científica

É possível reconstruir fielmente o esquema de reação e validar os dados estacionários Aspen armazenados. A reprodução numérica exata de MAE/RMSE e malha FKE+PI de 2016 permanece não identificada sem os arquivos finais ausentes. Um benchmark atual deve marcar claramente `FKE + PI reconstruído`, informar escolhas novas e reportar as métricas publicadas separadamente. A formulação de fração molar deve ser x_i = C_i/sum(C), a menos que uma definição explícita de densidade molar constante seja comprovada no código histórico.
