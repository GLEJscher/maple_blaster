from __future__ import annotations
import math

## 스탯창 스펙

class CharaInfo:
    def __init__(self, level=0, mainStat=0, subStat=0, mainStatp=0, subStatp=0,
                 fixedMainStat=0, fixedSubStat=0, attack=0, attackp=0, damage=0,
                 bossDamage=0, armorIgnore=0.0, finalDamage=0.0,
                 critDamage=0.0, attribResist=0, buffDuration=0, cooldown=0,
                 bosslevel=275):
        self.level = level
        self.mainStat = mainStat
        self.subStat = subStat
        self.mainStatp = mainStatp
        self.subStatp = subStatp
        self.fixedMainStat = fixedMainStat
        self.fixedSubStat = fixedSubStat
        self.attack = attack
        self.attackp = attackp
        self.damage = damage
        self.bossDamage = bossDamage
        self.armorIgnore = armorIgnore
        self.weaponConstant = 1.7
        self.finalDamage = finalDamage
        self.critDamage = critDamage
        self.attribResist = attribResist
        self.proficiency =  (1 + 0.91)/2
        self.buffDuration = buffDuration
        self.cooldown = cooldown
        # self.cooldownp = cooldownp
        self.cooldownp = 0.06
        self.bossLevelGap = 5


    def __add__(self, arg: CharaInfo) -> CharaInfo:
        return CharaInfo(
            level = self.level,
            mainStat = self.mainStat + arg.mainStat,
            subStat = self.subStat + arg.subStat,
            mainStatp = self.mainStatp + arg.mainStatp,
            subStatp = self.subStatp + arg.subStatp,
            fixedMainStat = self.fixedMainStat + arg.fixedMainStat,
            fixedSubStat = self.fixedSubStat + arg.fixedSubStat,
            attack = self.attack + arg.attack,
            attackp = self.attackp + arg.attackp,
            damage = self.damage + arg.damage,
            bossDamage = self.bossDamage + arg.bossDamage,
            armorIgnore = 100 - 0.01*(100 - self.armorIgnore)*(100 - arg.armorIgnore),
            # weaponConstant= self.weaponConstant,
            finalDamage = ((1+self.finalDamage*0.01) * (1+arg.finalDamage*0.01) - 1)*100,
            critDamage = self.critDamage + arg.critDamage,
            attribResist = self.attribResist + arg.attribResist,
            # proficiency= self.proficiency,
            buffDuration = self.buffDuration + arg.buffDuration,
            cooldown = self.cooldown + arg.cooldown)
            # cooldownp = self.cooldownp)
    
    def __sub__(self, arg: CharaInfo) -> CharaInfo:
        return CharaInfo(
            level = self.level,
            mainStat = self.mainStat - arg.mainStat,
            subStat = self.subStat - arg.subStat,
            mainStatp = self.mainStatp - arg.mainStatp,
            subStatp = self.subStatp - arg.subStatp,
            fixedMainStat = self.fixedMainStat - arg.fixedMainStat,
            fixedSubStat = self.fixedSubStat - arg.fixedSubStat,
            attack = self.attack - arg.attack,
            attackp = self.attackp - arg.attackp,
            damage = self.damage - arg.damage,
            bossDamage = self.bossDamage - arg.bossDamage,
            armorIgnore = 100 - 100*(100 - self.armorIgnore)/(100 - arg.armorIgnore),
            # weaponConstant= self.weaponConstant,
            finalDamage = ((1+self.finalDamage*0.01) / (1+arg.finalDamage*0.01) - 1)*100,
            critDamage = self.critDamage - arg.critDamage,
            attribResist = self.attribResist - arg.attribResist,
            # proficiency= self.proficiency,
            buffDuration = self.buffDuration - arg.buffDuration,
            cooldown = self.cooldown - arg.cooldown)
            # cooldownp = self.cooldownp)

    def __iadd__(self, arg):
        self.mainStat += arg.mainStat
        self.subStat += arg.subStat
        self.mainStatp += arg.mainStatp
        self.subStatp += arg.subStatp
        self.fixedMainStat += arg.fixedMainStat
        self.fixedSubStat += arg.fixedSubStat
        self.attack += arg.attack
        self.attackp += arg.attackp
        self.damage += arg.damage
        self.bossDamage += arg.bossDamage
        self.armorIgnore = 100 - 0.01*(100 - self.armorIgnore)*(100 - arg.armorIgnore)
        self.finalDamage = ((1+self.finalDamage*0.01) * (1+arg.finalDamage*0.01) - 1)*100
        self.critDamage += arg.critDamage
        self.attribResist += arg.attribResist
        self.buffDuration += arg.buffDuration
        self.cooldown += arg.cooldown
        return self

    def get_DPL(self, armor=380):
        totalStat = (4*math.floor(self.mainStat*(1+0.01*self.mainStatp) + self.fixedMainStat) + 
                     math.floor(self.subStat*(1+0.01*self.subStatp) + self.fixedSubStat)) * 0.01
        totalAttack = math.floor(self.attack * (1 + self.attackp * 0.01))
        totalDamage = 1 + 0.01 * (self.damage + self.bossDamage)
        totalProficiency = self.proficiency
        totalWeaponConstant = self.weaponConstant
        totalCritDamage = 1 + 0.01 * (35 + self.critDamage)
        totalAttribResistIgnore = 1 - 0.5 * (1 - 0.01 * self.attribResist)
        totalArmorIgnore = 1 - 0.01 * armor * (1 - 0.01 * self.armorIgnore)
        totalFinalDamage = 1 + 0.01 * self.finalDamage
        levelGapFD = 1.2
        
        return totalStat * totalAttack * totalDamage * totalProficiency * totalWeaponConstant * \
            totalCritDamage * totalAttribResistIgnore * totalArmorIgnore * totalFinalDamage * levelGapFD

# 렙뻥 캐릭터-보스가 +5 이상이면 최종뎀 120%
# 보스 렙뻥 = 1.2