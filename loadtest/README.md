# Teste de carga

Script único, só com a biblioteca padrão do Python 3.9+ (nada para instalar).
Rode de **uma máquina fixa** (seu notebook ou uma VM pequena) contra cada implantação.

```bash
# infraestrutura básica (rede + balanceador + banco), sem login
python loadtest.py --url https://SEU-APP -s health  -c 1,10,50,100 -d 30 --rotulo aws-ecs --csv resultados.csv

# consulta ao banco com usuários logados
python loadtest.py --url https://SEU-APP -s leitura -c 1,10,50 -d 30 --rotulo aws-ecs --csv resultados.csv

# CPU (bcrypt no login)
python loadtest.py --url https://SEU-APP -s login   -c 1,5,20 -d 20 --rotulo aws-ecs --csv resultados.csv

# correção: N pacientes disputam o mesmo horário (esperado: 1 ganha, N-1 recebem 409)
python loadtest.py --url https://SEU-APP -s reserva -c 20 --rodadas 5 --rotulo aws-ecs --csv resultados.csv
```

Requer o banco com `SEED=1`. Cada nível roda 5 s de aquecimento (descartados) + a duração pedida.
Repita 3 vezes por nível e use a mediana. O CSV acumula todas as rodadas (uma linha por nível).

O cenário `reserva` cadastra N pacientes `carga-*@marquefacil.test` e devolve os horários que reservou; os
pacientes ficam no banco (apague-o ou recrie com `SEED=1` antes da rodada seguinte, para igualar o ponto de partida).

Atenção: não rode contra o serviço de outra pessoa. Teste de carga em app alheio pode ser tratado como ataque.
